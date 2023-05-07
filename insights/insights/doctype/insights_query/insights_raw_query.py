# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import pandas as pd

from .utils import infer_type_from_list


class InsightsRawQueryController:
    def __init__(self, doc):
        self.doc = doc

    def after_reset(self):
        self.doc.is_native_query = 1

    def get_sql(self):
        return self.doc.sql

    def get_columns(self):
        if not hasattr(self.doc, "_results"):
            results = self.doc.retrieve_results()
        else:
            results = self.doc._results

        if not results:
            return []
        columns = results[0]
        column_names = [column.label for column in columns]
        results_df = pd.DataFrame(results[1:], columns=column_names)
        for column in columns:
            column.type = infer_type_from_list(results_df[column.label])
        return columns

    def before_fetch(self):
        pass

    def after_fetch_results(self, results):
        pass
