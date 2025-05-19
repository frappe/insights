# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import frappe.client
import ibis
from frappe.defaults import get_user_default, set_user_default
from frappe.integrations.utils import make_post_request
from frappe.monitor import add_data_to_monitor
from frappe.rate_limiter import rate_limit

from insights.api.shared import check_public_access
from insights.decorators import insights_whitelist, validate_type
from insights.insights.doctype.insights_data_source_v3.connectors.duckdb import (
    get_duckdb_connection,
)
from insights.insights.doctype.insights_data_source_v3.ibis_utils import (
    get_columns_from_schema,
)
from insights.insights.doctype.insights_table_v3.insights_table_v3 import (
    InsightsTablev3,
)
from insights.insights.doctype.insights_team.insights_team import (
    check_data_source_permission,
)


@insights_whitelist()
def get_app_version():
    return frappe.get_attr("insights" + ".__version__")


@insights_whitelist()
def get_user_info():
    is_admin = frappe.db.exists(
        "Has Role",
        {
            "parenttype": "User",
            "parent": frappe.session.user,
            "role": ["in", ("Insights Admin")],
        },
    )
    is_user = frappe.db.exists(
        "Has Role",
        {
            "parenttype": "User",
            "parent": frappe.session.user,
            "role": ["in", ("Insights User")],
        },
    )

    user = frappe.db.get_value("User", frappe.session.user, ["first_name", "last_name"], as_dict=1)

    return {
        "email": frappe.session.user,
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "is_admin": is_admin or frappe.session.user == "Administrator",
        "is_user": is_user or frappe.session.user == "Administrator",
        # TODO: move to `get_session_info` since not user specific
        "country": frappe.db.get_single_value("System Settings", "country"),
        "locale": frappe.db.get_single_value("System Settings", "language"),
        "is_v2_instance": frappe.db.count("Insights Query") > 0,
        "default_version": get_user_default("insights_default_version", frappe.session.user),
    }


@insights_whitelist()
def update_default_version(version):
    if get_user_default("insights_has_visited_v3", frappe.session.user) != "1":
        set_user_default("insights_has_visited_v3", "1", frappe.session.user)

    set_user_default("insights_default_version", version, frappe.session.user)


@frappe.whitelist()
@rate_limit(limit=10, seconds=60 * 60)
def contact_team(message_type, message_content, is_critical=False):
    if not message_type or not message_content:
        frappe.throw("Message Type and Content are required")

    message_title = {
        "Feedback": "Feedback from Insights User",
        "Bug": "Bug Report from Insights User",
        "Question": "Question from Insights User",
    }.get(message_type)

    if not message_title:
        frappe.throw("Invalid Message Type")

    try:
        make_post_request(
            "https://frappeinsights.com/api/method/contact-team",
            data={
                "message_title": message_title,
                "message_content": message_content,
            },
        )
    except Exception as e:
        frappe.log_error(e)
        frappe.throw("Something went wrong. Please try again later.")


def get_csv_file(filename: str):
    file = frappe.get_doc("File", filename)
    parts = file.get_extension()
    if "csv" not in parts[1]:
        frappe.throw("Only CSV files are supported")
    return file


@insights_whitelist()
@validate_type
def get_csv_data(filename: str):
    check_data_source_permission("uploads")

    file = get_csv_file(filename)
    file_path = file.get_full_path()
    file_name = file.file_name.split(".")[0]
    file_name = frappe.scrub(file_name)
    table = ibis.read_csv(file_path, table_name=file_name)
    count = table.count().execute().item()

    columns = get_columns_from_schema(table.schema())
    rows = table.head(50).execute().fillna("").to_dict(orient="records")

    return {
        "tablename": file_name,
        "rows": rows,
        "columns": columns,
        "total_rows": count,
    }


@insights_whitelist()
@validate_type
def import_csv_data(filename: str):
    check_data_source_permission("uploads")

    file = get_csv_file(filename)
    file_path = file.get_full_path()
    table_name = file.file_name.split(".")[0]
    table_name = frappe.scrub(table_name)

    if not frappe.db.exists("Insights Data Source v3", "uploads"):
        uploads = frappe.new_doc("Insights Data Source v3")
        uploads.name = "uploads"
        uploads.title = "Uploads"
        uploads.database_type = "DuckDB"
        uploads.database_name = "insights_file_uploads"
        uploads.owner = "Administrator"
        uploads.status = "Active"
        uploads.db_insert()

    ds = frappe.get_doc("Insights Data Source v3", "uploads")
    db = get_duckdb_connection(ds, read_only=False)

    try:
        table = db.read_csv(file_path, table_name=table_name)
        db.create_table(table_name, table, overwrite=True)
    finally:
        db.disconnect()

    InsightsTablev3.bulk_create(ds.name, [table_name])


@frappe.whitelist(allow_guest=True)
@validate_type
def get_doc(doctype: str, name: str | int):
    from frappe.client import get as _get_doc

    if frappe.session.user != "Guest":
        return _get_doc(doctype, name)

    check_public_access(doctype, name)

    return frappe.get_doc(doctype, name).as_dict()


@frappe.whitelist(allow_guest=True)
def run_doc_method(method: str, docs: dict | str, args: dict | None = None):
    from frappe.handler import run_doc_method as _run_doc_method

    if frappe.session.user != "Guest":
        return _run_doc_method(method, docs=docs, args=args)

    doc = frappe.parse_json(docs)
    doctype = doc.get("doctype")
    name = doc.get("name")

    if not doctype or not name:
        raise frappe.ValidationError("Invalid document")

    doc = frappe.get_doc(doctype, name)
    check_public_access(doctype, name)

    args = args or {}

    response = None
    if doctype == "Insights Query v3" and method in ("execute", "download_results"):
        response = doc.execute(**args)
    elif doctype == "Insights Dashboard v3" and method == "get_distinct_column_values":
        response = doc.get_distinct_column_values(**args)
    else:
        raise frappe.PermissionError("You don't have permission to access this document")

    frappe.response.docs.append(doc)
    frappe.response["message"] = response

    add_data_to_monitor(methodname=method)
