# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.database.mariadb.database import MariaDBDatabase
from frappe.model.document import Document


class DataSource(Document):
    def create_db_instance(self):
        if self.database_type == "MariaDB":
            self.db_instance = MariaDBDatabase(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
            )

    @frappe.whitelist()
    def test_connection(self):
        self.create_db_instance()
        self.db_instance.connect()
        user_exists = self.db_instance.a_row_exists("User")
        self.db_instance.close()
        if user_exists:
            frappe.msgprint("Connection Successful", alert=True)
