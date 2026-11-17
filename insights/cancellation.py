# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Stop a query whose reader left: a closed dashboard, a changed filter, a reload.

The client names each request with an id, and asks for the ids it no longer
waits on to stop. A cancel can land in any process, so it is a key in Redis.
The process that runs the query looks for it, and stops the query itself: a
data store query by DuckDB's `interrupt()` from its time-limit thread, which
polls the key while the query runs. A live MariaDB query registers its
connection, and the cancel stops it with `KILL QUERY` from the cancelling
request.

Ids are scoped to the user who sent them (a guest by address), so a reader can
stop only their own requests.
"""

import re
from contextlib import contextmanager

import frappe

import insights
from insights.resources import holder_name

REQUEST_ID_HEADER = "X-Insights-Request-Id"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")
# a cancel that lands before its query starts must still be there when it does
CANCEL_SECONDS = 5 * 60
MAX_CANCELS = 50


def current_request_id() -> str | None:
    request_id = (
        frappe.get_request_header(REQUEST_ID_HEADER) if getattr(frappe.local, "request", None) else None
    )
    if request_id and REQUEST_ID_PATTERN.match(request_id):
        return request_id
    return None


def _key(kind: str, request_id: str) -> bytes:
    return frappe.cache.make_key(f"insights:query_{kind}:{holder_name()}:{request_id}")


def cancel(request_ids: list[str]) -> None:
    """Ask the queries of `request_ids` to stop, in whichever process runs them."""
    for request_id in [r for r in request_ids if isinstance(r, str) and REQUEST_ID_PATTERN.match(r)][
        :MAX_CANCELS
    ]:
        # the flag first: a live query registers before it looks for one, so
        # one of the two sides sees the other
        # nosemgrep - the key comes from make_key, which prefixes the site
        frappe.cache.set(_key("cancel", request_id), 1, ex=CANCEL_SECONDS)
        # nosemgrep - the key comes from make_key, which prefixes the site
        if running := frappe.cache.get(_key("running", request_id)):
            data_source, connection_id = frappe.parse_json(running.decode())
            _kill_query(data_source, connection_id)


def _kill_query(data_source: str, connection_id: int) -> None:
    try:
        db = frappe.get_doc("Insights Data Source v3", data_source)._get_ibis_backend()
        db.raw_sql(f"KILL QUERY {int(connection_id)}")
    except Exception:
        # the query may have ended, and its connection with it
        frappe.log_error(title=f"Could not stop a query on {data_source}")


def cancel_requested(request_id: str | None):
    """A check, safe to call from another thread, of whether `request_id` was
    cancelled. `None` when the request has no id."""
    if not request_id:
        return None
    key = _key("cancel", request_id)

    def requested() -> bool:
        try:
            return bool(frappe.cache.execute_command("EXISTS", key))
        except Exception:
            return False  # nosemgrep - with Redis down a query runs to its time limit

    return requested


def was_cancelled() -> bool:
    check = cancel_requested(current_request_id())
    return bool(check and check())


@contextmanager
def cancellable_live_query(backend):
    """Let a cancel stop the live query `backend` runs inside this block.

    Only MariaDB, which stops a query from another connection by its id.
    """
    request_id = current_request_id()
    data_source = next((name for name, db in insights.db_connections.items() if db is backend), None)
    if not request_id or not data_source or getattr(backend, "name", None) != "mysql":
        yield
        return

    key = _key("running", request_id)
    # nosemgrep - the key comes from make_key, which prefixes the site
    frappe.cache.set(key, frappe.as_json([data_source, backend.con.thread_id()]), ex=CANCEL_SECONDS)
    try:
        if was_cancelled():
            raise_cancelled()
        yield
    finally:
        frappe.cache.delete(key)


def raise_cancelled(cause: BaseException | None = None):
    from insights.exceptions import QueryCancelled

    raise QueryCancelled(frappe._("The query was stopped because its reader left.")) from cause
