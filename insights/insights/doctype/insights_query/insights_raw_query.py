# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from .utils import get_columns_with_inferred_types


class InsightsRawQueryController:
    def __init__(self, doc):
        self.doc = doc

    def validate(self):
        pass

    def after_reset(self):
        self.doc.is_native_query = 1

    def get_sql(self):
        return self.doc.sql

    def get_columns(self, results=None):
        if not results:
            results = self.doc.retrieve_results()
        if not results:
            return []
        return get_columns_with_inferred_types(results)

    def get_columns_from_results(self, results):
        return self.get_columns(results)

    def before_fetch(self):
        pass

    def after_fetch_results(self, results):
        return results

    def get_tables_columns(self):
        return []
