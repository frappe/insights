# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe

test_dependencies = ["Insights Data Source", "Insights Table"]


class TestFrappeDBDataSource(unittest.TestCase):
    def setUp(self) -> None:
        self.data_source = make_test_data_source()

    def tearDown(self) -> None:
        self.data_source.delete()

    def test_connection(self):
        self.assertTrue(self.data_source.test_connection())

    def test_sync_tables(self):
        self.data_source.sync_tables(tables=["tabUser", "tabToDo"])
        insights_tables = frappe.get_all(
            "Insights Table", filters={"data_source": self.data_source.name}
        )
        self.assertEqual(len(insights_tables), 2)

    def test_column_options(self):
        options = self.data_source.get_column_options("tabUser", "name", "admin")
        self.assertTrue(options)
        self.assertEqual(options[0], "Administrator")


def make_test_data_source():
    data_source = frappe.new_doc("Insights Data Source")
    data_source.title = "Test Data Source"
    data_source.database_type = "MariaDB"
    data_source.database_name = frappe.conf.db_name
    data_source.username = frappe.conf.db_name
    data_source.password = frappe.conf.db_password
    data_source.host = frappe.conf.db_host or "localhost"
    data_source.port = frappe.conf.db_port or 3306
    data_source.save()
    return data_source
