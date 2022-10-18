# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from insights.insights.doctype.insights_query.insights_query import InsightsQuery


class BaseDataSource:
    data_source = None
    connection = None
    query_builder = None
    table_factory = None

    def test_connection(self):
        raise NotImplementedError

    def build_query(self, query: InsightsQuery):
        raise NotImplementedError

    def execute_query(self, query: str):
        raise NotImplementedError

    def sync_tables(self):
        raise NotImplementedError

    def get_columns(self, table_name: str):
        raise NotImplementedError

    def get_column_values(self):
        raise NotImplementedError

    def get_table_list(self):
        raise NotImplementedError

    def describe_table(self):
        raise NotImplementedError
