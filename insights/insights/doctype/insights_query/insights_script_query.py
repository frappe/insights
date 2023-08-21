# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import pandas as pd
from frappe.utils.safe_exec import compile_restricted, get_safe_globals

from insights import notify

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

    def fetch_results(self):
        script = self.doc.script
        if not script:
            return []

        results = []
        try:
            self.reset_script_log()
            variables = self.doc.get("variables") or []
            variables = {var.variable_name: var.variable_value for var in variables}
            _locals = {"results": results, **variables}
            exec(
                compile_restricted(script, filename="<scriptquery>"),
                get_safe_exec_globals(),
                _locals,
            )
            self.update_script_log()
            results = _locals["results"]
        except BaseException as e:
            frappe.log_error(title="Insights Script Query Error")
            frappe.throw(
                f"Error while executing script: {e}",
                title="Insights Script Query Error",
            )

        results = self.validate_results(results)
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

    def validate_results(self, results):
        if not results:
            notify("The script should declare a variable named 'results'.")
            return []

        if not isinstance(results[0], list):
            notify("Results should be a list of lists.")
            return []

        if not all(isinstance(row, list) for row in results):
            notify("All rows should be lists.")
            return []

        results[0] = [{"label": col} for col in results[0]]
        return results

    def before_fetch(self):
        return

    def after_fetch(self, results):
        return results

    def get_tables_columns(self):
        return []

    def get_selected_tables(self):
        return []


def get_safe_exec_globals():
    safe_globals = get_safe_globals()

    pandas = frappe._dict()
    pandas.DataFrame = pd.DataFrame
    pandas.read_csv = pd.read_csv
    pandas.json_normalize = pd.json_normalize
    # mock out to_csv and to_json to prevent users from writing to disk
    pandas.DataFrame.to_csv = lambda *args, **kwargs: None
    pandas.DataFrame.to_json = lambda *args, **kwargs: None
    safe_globals.pandas = pandas

    return safe_globals
