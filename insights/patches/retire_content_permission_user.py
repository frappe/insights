import frappe

CONTENT = ("Insights Chart v3", "Insights Dashboard v3")
FIELD = "permission_user"


def execute():
    """Drop the column that named the user a published chart or dashboard ran as.

    `run_as_owner` and `owner` answer it, so nothing may read a name that is
    no longer the answer.

    `Insights Alert` keeps its own `permission_user`: a scheduled run has no
    caller at all, so the user it was enabled by is the only answer there is.
    """
    for doctype in CONTENT:
        if FIELD in frappe.db.get_table_columns(doctype):
            frappe.db.sql_ddl(f"alter table `tab{doctype}` drop column `{FIELD}`")  # nosemgrep
