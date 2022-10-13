# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re
import frappe
from .models import BaseDataSource
from .utils import FrappeSiteConnection, get_site_db_connection
from insights.insights.query_builders.frappe_qb import FrappeQueryBuilder


class QueryStore(BaseDataSource):
    def __init__(self):
        self.connection: FrappeSiteConnection = get_site_db_connection()
        self.query_builder: FrappeQueryBuilder = FrappeQueryBuilder()
        self.query_runner = None  # not needed
        self.data_importer = None  # not needed

    def import_data(self):
        pass

    def query(self, query, *args, **kwargs):
        self.validate_query(query)
        self.create_temporary_tables(query)
        result = self.execute(query, *args, **kwargs)
        self.connection.close()
        return result

    def create_temporary_tables(self, query):
        tables = re.findall(r"from\s+`?([a-zA-Z0-9_-]+)`?", query, re.IGNORECASE)
        for table in tables:
            self.create_temporary_table(table)

    def create_temporary_table(self, table):
        if not frappe.db.exists("Insights Query", table):
            return

        # create temporary table for an existing insights query
        query = frappe.get_doc("Insights Query", table)
        columns = query.get_columns()
        result = query.load_result()

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

        self.execute(create_table)
        # since "create temporary table" doesn't cause an implict commit
        # to avoid "implicit commit" error from frappe/database.py -> check_implict_commit
        self.connection._connection.transaction_writes -= 1
        self.execute(insert_records, values=rows)

    def validate_query(self, query):
        if not query.strip().lower().startswith(("select", "explain")):
            raise frappe.ValidationError(
                "Only SELECT and EXPLAIN statements are allowed in Query Store"
            )

    def execute(self, query: str, *args, **kwargs):
        # doesn't close the connection after execution
        try:
            return self.connection.get().sql(query, *args, **kwargs)
        except Exception as e:
            # close the connection if there is an error
            self.connection.close()
            frappe.log_error(f"Error fetching data from QueryStore: {e}")
            raise

    def describe_table(self, table, limit=20):
        self.create_temporary_table(table)
        columns = self.execute(f"""desc `{table}`""")
        data = self.execute(f"""select * from `{table}` limit {limit}""")
        no_of_rows = self.execute(f"""select count(*) from `{table}`""")[0][0]
        self.connection.close()
        return columns, data, no_of_rows

    def get_distinct_column_values(self, column, search_text=None, limit=25):
        if not frappe.db.exists("Insights Query", column.get("table")):
            return []

        query = frappe.get_cached_doc("Insights Query", column.get("table"))
        Table = frappe.qb.Table(column.get("table"))
        Column = frappe.qb.Field(column.get("column"))
        query = frappe.qb.from_(Table).select(Column).distinct().limit(limit)
        if search_text:
            query = query.where(Column.like(f"%{search_text}%"))

        return self.query(query.get_sql())
