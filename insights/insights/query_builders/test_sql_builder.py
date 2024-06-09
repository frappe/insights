# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe

from .sql_builder import SQLQueryBuilder


class TestSQLBuilder(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        conn_args = {
            "data_source": "Test Site Connection",
            "database_name": frappe.conf.db_name,
            "username": frappe.conf.db_name,
            "password": frappe.conf.db_password,
            "host": "localhost",
            "port": 3306,
            "use_ssl": False,
        }

        from insights.insights.doctype.insights_data_source.sources.frappe_db import (
            FrappeDB,
        )

        frappe_db = FrappeDB(**conn_args)
        self.assertTrue(frappe_db.test_connection())
        self.site_db = frappe_db

    def test_query(self):
        builder = SQLQueryBuilder()
        doc = frappe.get_doc(TEST_QUERY)
        sql = builder.build(doc, dialect=self.site_db.engine.dialect)
        self.assertTrue(sql)

    def test_joins(self):
        from sqlalchemy import column, select, table, text

        todo = table(
            "tabToDo", column("name"), column("allocated_to"), column("reference_name")
        )
        user = table("tabUser", column("name"), column("full_name"))
        comment = table("tabComment", column("name"))

        query = (
            select(text("count(*)"))
            .select_from(todo)
            .join(user, todo.c.allocated_to == user.c.name)
            .outerjoin(comment, todo.c.reference_name == comment.c.name)
            .where(user.c.full_name == "Administrator")
        )

        self.site_db.execute_query(query)

    def test_date_ranges(self):
        from frappe.utils.data import get_date_str

        from .sql_builder import get_date_range

        nowdate_path = "insights.insights.query_builders.sql_builder.nowdate"
        with patch(nowdate_path, return_value="2022-11-26"):
            assertions_map = {
                "Current Day": ["2022-11-26", "2022-11-26"],
                "Current Week": ["2022-11-20", "2022-11-26"],
                "Current Month": ["2022-11-01", "2022-11-30"],
                "Current Quarter": ["2022-10-01", "2022-12-31"],
                "Current Year": ["2022-01-01", "2022-12-31"],
                "Last 1 Day": ["2022-11-25", "2022-11-25"],
                "Last 1 Week": ["2022-11-13", "2022-11-19"],
                "Last 1 Month": ["2022-10-01", "2022-10-31"],
                "Last 1 Quarter": ["2022-07-01", "2022-09-30"],
                "Last 1 Year": ["2021-01-01", "2021-12-31"],
                "Next 1 Day": ["2022-11-27", "2022-11-27"],
                "Next 1 Week": ["2022-11-27", "2022-12-03"],
                "Next 1 Month": ["2022-12-01", "2022-12-31"],
                "Next 1 Quarter": ["2023-01-01", "2023-03-31"],
                "Next 1 Year": ["2023-01-01", "2023-12-31"],
            }
            for key, value in assertions_map.items():
                dates = [get_date_str(d) for d in get_date_range(key)]
                self.assertEqual(dates, value)

            assertions_with_include_current = {
                "Current Day": ["2022-11-26", "2022-11-26"],
                "Current Week": ["2022-11-20", "2022-11-26"],
                "Current Month": ["2022-11-01", "2022-11-30"],
                "Current Quarter": ["2022-10-01", "2022-12-31"],
                "Current Year": ["2022-01-01", "2022-12-31"],
                "Last 1 Day": ["2022-11-25", "2022-11-26"],
                "Last 1 Week": ["2022-11-13", "2022-11-26"],
                "Last 1 Month": ["2022-10-01", "2022-11-30"],
                "Last 1 Quarter": ["2022-07-01", "2022-12-31"],
                "Last 1 Year": ["2021-01-01", "2022-12-31"],
                "Next 1 Day": ["2022-11-26", "2022-11-27"],
                "Next 1 Week": ["2022-11-20", "2022-12-03"],
                "Next 1 Month": ["2022-11-01", "2022-12-31"],
                "Next 1 Quarter": ["2022-10-01", "2023-03-31"],
                "Next 1 Year": ["2022-01-01", "2023-12-31"],
            }
            for key, value in assertions_with_include_current.items():
                dates = [get_date_str(d) for d in get_date_range(key, True)]
                self.assertEqual(dates, value)


TEST_QUERY = {
    "doctype": "Insights Query",
    "title": "Test Todo Count",
    "data_source": "Site DB",
    "tables": [
        {
            "label": "ToDo",
            "table": "tabToDo",
            "doctype": "Insights Query Table",
            "join": {
                "type": {"label": "Right", "value": "right"},
                "with": {"label": "User", "value": "tabUser"},
                "condition": {
                    "left": {"label": "owner", "value": "owner"},
                    "right": {"label": "name", "value": "name"},
                },
            },
        },
    ],
    "columns": [
        {
            "label": "Name",
            "column": "name",
            "doctype": "Insights Query Column",
            "table": "tabToDo",
            "table_label": "ToDo",
        },
        {
            "label": "Due Date",
            "column": "date",
            "type": "Date",
            "table": "tabToDo",
            "table_label": "ToDo",
            "aggregation": "Group By",
            "format_option": '{\n  "date_format": "Month"\n}',
            "doctype": "Insights Query Column",
        },
    ],
    "filters": {
        "type": "LogicalExpression",
        "operator": "&&",
        "level": 1,
        "position": 1,
        "conditions": [
            {
                "type": "BinaryExpression",
                "operator": "=",
                "left": {
                    "type": "Column",
                    "value": {"column": "status", "table": "tabToDo"},
                },
                "right": {"type": "String", "value": "Open"},
            }
        ],
    },
}
