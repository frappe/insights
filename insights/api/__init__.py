# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os

import frappe
from frappe.defaults import get_user_default, set_user_default
from frappe.handler import is_valid_http_method, is_whitelisted
from frappe.monitor import add_data_to_monitor

from insights.api.shared import is_public
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

    user = frappe.db.get_value(
        "User", frappe.session.user, ["first_name", "last_name", "user_type", "language"], as_dict=1
    )

    locale = user.get("language") or frappe.db.get_single_value("System Settings", "language") or "en"

    _is_admin = is_admin or frappe.session.user == "Administrator"

    has_demo_data = False
    if _is_admin:
        from insights.setup.setup_wizard import check_demo_data_exists

        has_demo_data = check_demo_data_exists()

    return {
        "email": frappe.session.user,
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "is_admin": _is_admin,
        "is_user": is_user or frappe.session.user == "Administrator",
        # TODO: move to `get_session_info` since not user specific
        "country": frappe.db.get_single_value("System Settings", "country"),
        "locale": locale,
        "is_v2_instance": frappe.db.count("Insights Query") > 0,
        "default_version": get_user_default("insights_default_version", frappe.session.user),
        "has_desk_access": user.get("user_type") == "System User",
        "has_demo_data": has_demo_data,
    }


@insights_whitelist()
def update_default_version(version: str):
    if get_user_default("insights_has_visited_v3", frappe.session.user) != "1":
        set_user_default("insights_has_visited_v3", "1", frappe.session.user)

    set_user_default("insights_default_version", version, frappe.session.user)


def get_csv_file(filename: str):
    file = frappe.get_doc("File", filename)
    file_name = file.file_name or ""
    parts = file.get_extension()
    extension = parts[-1] if parts else ""
    extension = extension.lstrip(".")

    if not extension or extension not in ["csv", "xlsx", "json", "jsonl"]:
        frappe.throw(
            f"Only CSV, XLSX, JSON, and JSONL files are supported. Detected extension: '{extension}' from filename: '{file_name}'"
        )
    return file, extension


def create_uploads_if_not_exists():
    if not frappe.db.exists("Insights Data Source v3", "uploads"):
        uploads = frappe.new_doc("Insights Data Source v3")
        uploads.name = "uploads"
        uploads.title = "Uploads"
        uploads.database_type = "DuckDB"
        uploads.database_name = "insights_file_uploads"
        uploads.owner = "Administrator"
        uploads.status = "Active"
        uploads.insert(ignore_permissions=True)


@insights_whitelist()
@validate_type
def get_file_data(filename: str):
    check_data_source_permission("uploads")

    file, ext = get_csv_file(filename)
    file_path = file.get_full_path()
    file_name = file.file_name.split(".")[0]
    file_name = frappe.scrub(file_name)

    create_uploads_if_not_exists()
    ds = frappe.get_doc("Insights Data Source v3", "uploads")
    private_folder = frappe.utils.get_files_path(is_private=1)
    private_folder = os.path.realpath(private_folder)
    db = get_duckdb_connection(ds, read_only=True, allowed_dir=private_folder)
    try:
        if ext in ["xlsx"]:
            table = db.read_xlsx(file_path)
        elif ext in ["json", "jsonl"]:
            table = db.read_json(file_path)
        else:
            table = db.read_csv(file_path, table_name=file_name)

        columns = get_columns_from_schema(table.schema())
        rows = table.head(50).execute().fillna("").to_dict(orient="records")
        row_count = table.count().execute()
    finally:
        db.disconnect()

    return {
        "tablename": file_name,
        "rows": rows,
        "columns": columns,
        "total_rows": int(row_count),
    }


@insights_whitelist()
@validate_type
def import_csv_data(filename: str, tablename: str = ""):
    check_data_source_permission("uploads")

    file, ext = get_csv_file(filename)
    file_path = file.get_full_path()
    table_name = frappe.scrub(tablename) if tablename else frappe.scrub(file.file_name.split(".")[0])

    create_uploads_if_not_exists()
    ds = frappe.get_doc("Insights Data Source v3", "uploads")
    private_folder = os.path.realpath(frappe.utils.get_files_path(is_private=1))

    db = get_duckdb_connection(ds, read_only=False, allowed_dir=private_folder)
    try:
        if ext in ["xlsx"]:
            table = db.read_xlsx(file_path)
        elif ext in ["json", "jsonl"]:
            table = db.read_json(file_path)
        else:
            table = db.read_csv(file_path, table_name=table_name)
        db.create_table(table_name, table, overwrite=True)
    except Exception as e:
        frappe.log_error(e)
        if ext in ["xlsx"]:
            frappe.throw(
                "Failed to read Excel data from uploaded file. Please ensure the file is a valid Excel format and try again."
            )
        elif ext in ["json", "jsonl"]:
            frappe.throw(
                "Failed to read JSON data from uploaded file. Please ensure the file is a valid JSON or JSONL format and try again."
            )
        else:
            frappe.throw("Failed to read CSV data from uploaded file. Please try again.")
    finally:
        db.disconnect()

    InsightsTablev3.bulk_create(ds.name, [table_name])


@frappe.whitelist(allow_guest=True)
@validate_type
def get_doc(doctype: str, name: str | int):
    try:
        from frappe.client import get as _get_doc

        return _get_doc(doctype, name)
    except frappe.PermissionError:
        if not is_public(doctype, name):
            raise
        return frappe.get_doc(doctype, name).as_dict()


def _execute_doc_method(doc, method: str, args: dict | None = None, ignore_permissions=False):
    args = frappe.parse_json(args)
    method_obj = getattr(doc, method)
    fn = getattr(method_obj, "__func__", method_obj)

    if not ignore_permissions:
        doc.check_permission("read")
        is_whitelisted(fn)
        is_valid_http_method(fn)

    new_kwargs = frappe.get_newargs(fn, args)
    response = doc.run_method(method, **new_kwargs)
    frappe.response.docs.append(doc)
    frappe.response["message"] = response
    add_data_to_monitor(methodname=method)
    return response


@frappe.whitelist(allow_guest=True)
def run_doc_method(method: str, docs: dict | str, args: dict | None = None):
    doc = frappe.parse_json(docs)
    doctype = doc.get("doctype")
    name = doc.get("name")

    if not doctype or not name:
        raise frappe.ValidationError("Invalid document")

    try:
        docs = frappe.parse_json(docs)
        doc = frappe.get_doc(docs)
        return _execute_doc_method(doc, method, args)

    except frappe.PermissionError:
        if not is_public(doctype, name):
            raise frappe.PermissionError("You don't have permission to access this document")
        if not is_public_method(doctype, method):
            raise frappe.PermissionError("You don't have permission to access this method")

        doc = frappe.get_doc(doctype, name)
        frappe.flags.insights_for_public_access = True
        try:
            return _execute_doc_method(doc, method, args, ignore_permissions=True)
        finally:
            frappe.flags.insights_for_public_access = False


def is_public_method(doctype: str, method: str):
    public_methods = {
        "Insights Query v3": ["execute", "download_results"],
        "Insights Dashboard v3": ["get_distinct_column_values", "track_view"],
    }

    if doctype in public_methods and method in public_methods[doctype]:
        return True

    return False
