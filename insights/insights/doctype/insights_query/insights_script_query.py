# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import pandas as pd
import RestrictedPython.Guards
from frappe.utils.safe_exec import (
    FrappeTransformer,
    NamespaceDict,
    _getattr,
    _getitem,
    _write,
    add_data_utils,
    compile_restricted,
    get_python_builtins,
)

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
            _locals = {"results": results}
            exec(
                compile_restricted(script, filename="<scriptquery>", policy=FrappeTransformer),
                get_safe_exec_globals(),
                _locals,
            )
            results = _locals["results"]
            if isinstance(results, pd.DataFrame):
                # convert to list of lists where the first row is the column names
                results = results.values.tolist()
                results.insert(0, list(results.columns))
        except BaseException as e:
            frappe.log_error(title="Insights Script Query Error")
            frappe.throw(
                f"Error while executing script: {e}",
                title="Insights Script Query Error",
            )

        results = self.validate_results(results)
        return results

    def validate_results(self, results):
        if not results:
            frappe.throw("The script should declare a variable named 'results'.")

        if not isinstance(results[0], list):
            frappe.throw("Results should be a list of lists.")

        if not all(isinstance(row, list) for row in results):
            frappe.throw("All rows should be lists.")

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
    datautils = frappe._dict()
    add_data_utils(datautils)

    pandas = frappe._dict()
    pandas.DataFrame = pd.DataFrame
    pandas.read_csv = pd.read_csv
    pandas.json_normalize = pd.json_normalize
    # mock out to_csv and to_json to prevent users from writing to disk
    pandas.DataFrame.to_csv = lambda *args, **kwargs: None
    pandas.DataFrame.to_json = lambda *args, **kwargs: None

    out = NamespaceDict(
        utils=datautils,
        as_json=frappe.as_json,
        parse_json=frappe.parse_json,
        make_get_request=frappe.integrations.utils.make_get_request,
        pandas=pandas,
    )

    out._write_ = _write
    out._getitem_ = _getitem
    out._getattr_ = _getattr
    out._getiter_ = iter
    out._iter_unpack_sequence_ = RestrictedPython.Guards.guarded_iter_unpack_sequence
    out.update(get_python_builtins())

    return out
