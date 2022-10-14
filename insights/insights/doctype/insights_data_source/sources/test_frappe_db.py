# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest

test_dependencies = ["Insights Data Source", "Insights Table"]


class TestFrappeDBDataSource(unittest.TestCase):
    def setUp(self) -> None:
        self.data_source = create_frappe_db()

    def tearDown(self) -> None:
        self.data_source.delete(force=True)

    def test_connection(self):
        self.assertTrue(self.data_source.test_connection())

    def test_import_tables(self):
        # mock FrappeDB.get_table_list to import only two table
        self.data_source.source.data_importer.get_table_list = lambda: [
            frappe._dict({"name": "tabUser", "label": "User"}),
            frappe._dict({"name": "tabToDo", "label": "ToDo"}),
        ]
        self.data_source.import_data()
        insights_tables = frappe.get_all(
            "Insights Table", filters={"data_source": self.data_source.name}
        )
        self.assertEqual(len(insights_tables), 2)

    def test_running_jobs(self):
        self.data_source.get_running_jobs()


def create_frappe_db():
    source = frappe.get_doc(
        {
            "source_type": "Database",
            "title": "Test Frappe DB",
            "database_type": "MariaDB",
            "doctype": "Insights Data Source",
        }
    )
    source.host = "localhost"
    source.port = 3306
    source.username = frappe.conf.db_name
    source.password = frappe.conf.db_password
    source.database_name = frappe.conf.db_name
    source.save()
    return source
