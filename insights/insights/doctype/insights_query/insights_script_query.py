# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import pandas as pd
from frappe.utils.password import get_decrypted_password
from frappe.utils.safe_exec import safe_exec

from insights import notify
from insights.utils import ResultColumn

from .utils import get_columns_with_inferred_types


class ScriptQueryExecutionError(frappe.ValidationError):
    pass


class InsightsScriptQueryController:
    def __init__(self, doc):
        self.doc = doc

    def validate(self):
        pass

    def before_save(self):
        pass

    def get_columns_from_results(self, results):
        if not results:
            return []
        return get_columns_with_inferred_types(results)

    def fetch_results(self, additional_filters=None):
        script = self.doc.script
        if not script:
            return []

        def get_value(variable):
            return get_decrypted_password(variable.doctype, variable.name, "variable_value")

        results = []
        try:
            self.reset_script_log()
            variables = self.doc.get("variables") or []
            variables = {var.variable_name: get_value(var) for var in variables}
            _locals = {"results": results, **variables}
            safe_exec(
                script,
                _globals=get_globals(),
                _locals=_locals,
                restrict_commit_rollback=True,
            )
            self.update_script_log()
            results = _locals["results"]
        except Exception as e:
            frappe.log_error(title="Insights Script Query Error")
            frappe.throw(
                f"Error while executing script: {e}",
                title="Insights Script Query Error",
            )

        results = self.validate_and_sanitize_results(results)
        return results

    def reset_script_log(self):
        self.doc.db_set(
            "script_log",
            "",
            commit=True,
            update_modified=False,
        )

    def update_script_log(self):
        self.doc.db_set(
            "script_log",
            "\n".join(frappe.debug_log),
            commit=True,
            update_modified=False,
        )

    def validate_and_sanitize_results(self, results):
        if not results:
            notify(
                "The script should declare a variable named 'results' that contains column header and row data."
            )
            return []

        if isinstance(results, pd.DataFrame):
            columns = [ResultColumn.from_args(col) for col in results.columns]
            values = results.values.tolist()
            return [columns] + values

        if not all(isinstance(row, list) for row in results):
            notify("All rows should be lists.")
            return []

        if all(isinstance(col, str) for col in results[0]):
            new_columns = [ResultColumn.from_args(col) for col in results[0]]
            return [new_columns] + results[1:]

        return results

    def before_fetch(self):
        return

    def after_fetch(self, results):
        return results

    def get_tables_columns(self):
        return []

    def get_selected_tables(self):
        return []


def get_globals():
    pandas = frappe._dict()
    pandas.DataFrame = pd.DataFrame
    pandas.read_csv = pd.read_csv
    pandas.json_normalize = pd.json_normalize
    # mock out to_csv and to_json to prevent users from writing to disk
    pandas.DataFrame.to_csv = lambda *args, **kwargs: None
    pandas.DataFrame.to_json = lambda *args, **kwargs: None

    return {
        "pandas": pandas,
        "get_query_results": get_query_results,
    }


def get_query_results(query_name):
    if not isinstance(query_name, str):
        raise ScriptQueryExecutionError("Query name should be a string.")
    doc = frappe.get_doc("Insights Query", query_name)
    return doc.retrieve_results(fetch_if_not_cached=True)
