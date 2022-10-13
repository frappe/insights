# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import unittest


class TestFrappeDBDataSource(unittest.TestCase):
    def setUp(self) -> None:
        self.data_source = create_data_source()

    def tearDown(self) -> None:
        frappe.delete_doc("Insights Data Source", self.data_source.name, force=True)

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


def create_data_source():
    frappe.delete_doc("Insights Data Source", "Test Data Source", force=True)
    data_source = frappe.new_doc("Insights Data Source")
    data_source.source_type = "Database"
    data_source.title = "Test Data Source"
    data_source.database_type = "MariaDB"
    data_source.host = "localhost"
    data_source.port = 3306
    data_source.database_name = frappe.conf.db_name
    data_source.username = frappe.conf.db_name
    data_source.password = frappe.conf.db_password
    data_source.insert()
    return data_source
