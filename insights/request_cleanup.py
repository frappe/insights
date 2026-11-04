# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Request cleanup without loading the data-source and analytics stack."""

import sys
from contextlib import contextmanager

import frappe

import insights

DATA_WAREHOUSE = "insights.insights.doctype.insights_data_source_v3.data_warehouse"


def after_request():
    """Close request-scoped data-source connections and release its data-store slot."""
    connections = insights.db_connections
    closed = {}
    for name, db in connections.items():
        try:
            db.disconnect()
            closed[name] = True
        except Exception:
            frappe.log_error(title=f"Failed to disconnect db connection for {name}")

    for name in closed:
        del connections[name]

    if warehouse := sys.modules.get(DATA_WAREHOUSE):
        warehouse.release_data_store_slot()


@contextmanager
def db_connections():
    """Ensure database connections are cleaned up when the operation ends."""
    try:
        yield
    finally:
        after_request()
