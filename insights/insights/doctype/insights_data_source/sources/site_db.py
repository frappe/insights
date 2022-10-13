# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from .models import BaseDataSource
from .frappe_db import convert_to_insights_column_type
from .utils import FrappeSiteConnection, DatabaseQueryRunner, get_site_db_connection
from insights.insights.query_builders.frappe_qb import FrappeQueryBuilder


class SiteDB(BaseDataSource):
    def __init__(self):
        self.connection: FrappeSiteConnection = get_site_db_connection()
        self.query_builder: FrappeQueryBuilder = FrappeQueryBuilder()
        self.query_runner: DatabaseQueryRunner = DatabaseQueryRunner(self.connection)
        self.data_importer = None

    def describe_table(self, table, limit=20):
        columns = self.query(f"""desc `{table}`""")
        data = self.query(f"""select * from `{table}` limit {limit}""")
        no_of_rows = self.query(f"""select count(*) from `{table}`""")[0][0]
        return columns, data, no_of_rows

    # needed in insights_table.py
    def get_columns(self, table):
        query = """
            select column_name as name, data_type as type
            from information_schema.columns
            where table_name = %s
        """
        # TODO: caching
        columns = self.query_runner.execute(query, values=table, as_dict=1)
        columns = self.process_columns(columns)
        return columns

    def process_columns(self, columns):
        _columns = [
            {
                "column": d.name,
                "type": convert_to_insights_column_type(d.type),
                "label": frappe.unscrub(d.name).rstrip().lstrip(),
            }
            for d in columns
        ]
        return _columns

    def import_data(self):
        pass
