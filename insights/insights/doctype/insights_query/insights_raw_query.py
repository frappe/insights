# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe

from .utils import InsightsDataSource, get_columns_with_inferred_types, update_sql


class InsightsRawQueryController:
    def __init__(self, doc):
        self.doc = doc

    def validate(self):
        pass

    def before_save(self):
        update_sql(self.doc)

    def get_columns_from_results(self, results):
        if not results:
            return []
        return get_columns_with_inferred_types(results)

    def before_fetch(self):
        pass

    def after_fetch(self, results):
        return results

    def get_tables_columns(self):
        return []

    def get_selected_tables(self):
        return []

    def fetch_results(self, additional_filters=None):
        return InsightsDataSource.get_doc(self.doc.data_source).run_query(self.doc)

    def export_query(self):
        return {"sql": self.doc.sql}

    def import_query(self, exported_query):
        self.doc.sql = exported_query.get("sql")
