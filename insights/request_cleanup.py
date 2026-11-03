# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Request cleanup without loading the data-source and analytics stack."""

import threading
import time
from contextlib import contextmanager

import frappe

import insights


class ProcessSlot:
    """The data-store slots this process may hold.

    A hold ends with its pool lease, so a request whose release never ran does
    not lock its process out for good.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._holders = {}

    def acquire(self, capacity: int, hold: float) -> object | None:
        with self._lock:
            now = time.monotonic()
            self._holders = {h: until for h, until in self._holders.items() if until > now}
            if len(self._holders) >= capacity:
                return None
            holder = object()
            self._holders[holder] = now + hold
            return holder

    def release(self, holder: object):
        with self._lock:
            self._holders.pop(holder, None)


process_slots = ProcessSlot()


def release_data_store_slot():
    """Release the request's data-store lease and its per-process slot."""
    frappe.local.insights_data_store_started = None
    if slot := getattr(frappe.local, "insights_data_store_slot", None):
        frappe.local.insights_data_store_slot = None
        pool, lease, _started, process_slot = slot
        try:
            pool.release(lease)
        finally:
            process_slots.release(process_slot)


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

    # Close connections first, so the next holder does not meet this one's memory.
    release_data_store_slot()


@contextmanager
def db_connections():
    """Ensure database connections are cleaned up when the operation ends."""
    try:
        yield
    finally:
        after_request()
