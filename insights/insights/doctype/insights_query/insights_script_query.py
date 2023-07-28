# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils.safe_exec import safe_exec

from .utils import get_columns_with_inferred_types


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
            safe_exec(script, None, _locals)
            results = _locals["results"]
        except BaseException:
            frappe.log_error(title="Insights Script Query Error")
            frappe.throw(
                "There was an error executing the script. "
                "Please check the error log for more details.",
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

        if not all(isinstance(col, str) for col in results[0]):
            frappe.throw("All columns should be strings.")

        if not all(len(row) == len(results[0]) for row in results):
            frappe.throw("All rows should have the same number of columns.")

        if not all(col for col in results[0]):
            frappe.throw("All columns should have a label.")

        results[0] = [{"label": col.strip()} for col in results[0]]
        return results

    def before_fetch(self):
        return

    def after_fetch(self, results):
        return results

    def get_tables_columns(self):
        return []

    def get_selected_tables(self):
        return []
