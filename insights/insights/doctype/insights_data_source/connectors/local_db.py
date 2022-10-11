# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.database.mariadb.database import MariaDBDatabase

from insights.insights.doctype.insights_data_source.connectors.model import (
    BaseDataSource,
)


class AppDB(BaseDataSource):
    def create_connection(self):
        return MariaDBDatabase(
            user=frappe.conf.db_name,
            password=frappe.conf.db_password,
        )

    def test_connection(self):
        return True

    def get_test_query(self):
        return None

    def get_data(self, query, *args, **kwargs):
        try:
            return self.get_connection().sql(query, *args, **kwargs)
        except Exception as e:
            self.close_connection()
            frappe.log_error(f"Error fetching data from AppDB: {e}")
            raise

    def close_connection(self):
        self.connection.close() if self.connection else None

    def describe_table(self, table, limit=20):
        columns = self.get_data(f"""desc `{table}`""")
        data = self.get_data(f"""select * from `{table}` limit {limit}""")
        no_of_rows = self.get_data(f"""select count(*) from `{table}`""")[0][0]
        return columns, data, no_of_rows


class QueryStore(AppDB):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_query_store = True
        self.doc.flags.ignore_mandatory = True

    def describe_table(self, table, limit=20):
        columns, data, no_of_rows = [], [], 0
        if frappe.db.exists("Insights Query", table):
            self.create_temporary_table(table)
            columns = self.get_data(f"""desc `{table}`""")
            data = self.get_data(f"""select * from `{table}` limit {limit}""")
            no_of_rows = self.get_data(f"""select count(*) from `{table}`""")[0][0]
            self.close_connection()
        return columns, data, no_of_rows

    def create_temporary_table(self, table):
        query = frappe.get_doc("Insights Query", table)
        columns = query.get_columns()
        result = query.get_result()

        mysql_type_map = {
            "Time": "TIME",
            "Date": "DATE",
            "String": "VARCHAR(255)",
            "Integer": "INT",
            "Decimal": "FLOAT",
            "Datetime": "DATETIME",
            "Text": "TEXT",
        }

        _columns = []
        for row in columns:
            _columns.append(
                f"`{row.column or row.label}` {mysql_type_map.get(row.type, 'VARCHAR(255)')}"
            )

        id_column = ["TEMPID INT PRIMARY KEY AUTO_INCREMENT"]
        if "TEMPID" not in _columns[0]:
            _columns = id_column + _columns

        create_table = f"CREATE TEMPORARY TABLE `{query.name}`({', '.join(_columns)})"

        rows = []
        for i, row in enumerate(result):
            rows.append([i + 1] + list(row))
        insert_records = (
            f"INSERT INTO `{query.name}` VALUES {', '.join(['%s'] * len(rows))}"
        )

        self.flags.skip_validation = True
        self.get_data(create_table)
        # since "create temporary table" doesn't cause an implict commit
        # to avoid "implicit commit" error from frappe/database.py -> check_implict_commit
        self.connection.transaction_writes -= 1
        self.flags.skip_validation = True
        self.get_data(insert_records, values=rows)
