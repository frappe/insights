# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from typing import Protocol


class Source(Protocol):
    def get_connection(self):
        """creates or returns a connection to the source"""
        ...

    def create_connection(self):
        """creates the connection object"""
        ...

    def test_connection(self):
        """tests the connection to the source"""
        ...

    def get_test_query(self):
        ...

    def get_data(self):
        ...

    def get_insights_tables(self):
        """returns a list of table names to create insights tables from"""
        ...

    def create_insights_tables(self):
        """returns a list of table names to create insights tables from"""
        ...

    def describe_table(
        self, table_name: str, limit: int = 20
    ) -> "tuple[list, list, int]":
        """returns a list of columns and rows and no of rows for the given table"""
        ...


class BaseDataSource(Source):
    def __init__(self, doc=None):
        self.doc = doc
        self.flags = frappe._dict()

    def get_connection(self):
        if not hasattr(self, "connection") or not self.connection:
            self.connection = self.create_connection()
        # TODO: cache into site cache with key as self.name
        return self.connection

    def get_test_query(self) -> str:
        frappe.throw("Not Implemented")

    def create_connection(self):
        frappe.throw("Not Implemented")

    def test_connection(self):
        frappe.throw("Not Implemented")

    def get_data(self):
        frappe.throw("Not Implemented")

    def get_insights_tables(self):
        frappe.throw("Not Implemented")

    def create_insights_tables(self):
        frappe.throw("Not Implemented")

    def describe_table(self):
        frappe.throw("Not Implemented")
