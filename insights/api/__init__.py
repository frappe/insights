# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import ibis
from frappe.defaults import get_user_default, set_user_default
from frappe.integrations.utils import make_post_request
from frappe.rate_limiter import rate_limit

from insights.decorators import insights_whitelist, validate_type
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
        "User", frappe.session.user, ["first_name", "last_name"], as_dict=1
    )

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
        "default_version": get_user_default(
            "insights_default_version", frappe.session.user
        ),
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
    rows = table.head(50).execute().to_dict(orient="records")

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
        uploads.save(ignore_permissions=True)

    ds = frappe.get_doc("Insights Data Source v3", "uploads")
    db = ds._get_ibis_backend()

    table = db.read_csv(file_path, table_name=table_name)
    db.create_table(table_name, table, overwrite=True)

    InsightsTablev3.create(ds.name, table_name)
