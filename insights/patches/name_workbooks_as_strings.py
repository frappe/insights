import frappe
from frappe.utils import cint

from insights.insights.doctype.insights_workbook.insights_workbook import WORKBOOK_SERIES_KEY

SEQUENCE_NAME = frappe.scrub(f"{WORKBOOK_SERIES_KEY}_id_seq")


def execute():
    """
    `Insights Workbook` used to be named by `autoincrement`, which makes `name` a bigint.
    Every column that references a workbook is varchar(140) though — the four `workbook`
    Link fields, `View Log.reference_name` and `DocShare.share_name` — and postgres refuses
    `character varying = integer`, so listing or sharing a workbook failed outright
    (frappe/insights#1193).

    The doctype now names itself from `tabSeries`, which keeps the plain numbers but stores
    them as strings. This patch converts the column and hands the counter over.

    It has to run pre-model-sync: `validate_autoincrement_autoname` refuses to move a
    doctype that already holds data off `autoincrement`, so the DocType record must already
    say so before the new JSON is imported.
    """
    if not frappe.db.table_exists("Insights Workbook"):
        return

    if "bigint" not in str(frappe.db.get_column_type("Insights Workbook", "name")).lower():
        return

    # read the counter while the column is still numeric
    last_id = frappe.db.sql("select max(name) from `tabInsights Workbook`")[0][0]

    # the JSON that lands right after this patch no longer carries `autoname`; the DocType
    # record has to agree with it already, or the import throws
    frappe.db.set_value(
        "DocType",
        "Insights Workbook",
        {"autoname": "", "naming_rule": ""},
        update_modified=False,
    )
    frappe.clear_cache(doctype="Insights Workbook")

    frappe.get_doc("DocType", "Insights Workbook").setup_autoincrement_and_sequence()
    drop_sequence()
    seed_series(last_id)


def drop_sequence():
    """The sequence the old naming rule drew from. Nothing recreates it: the framework only
    maintains sequences for doctypes still marked `autoincrement`."""
    frappe.db.sql_ddl(f"drop sequence if exists {SEQUENCE_NAME}")


def seed_series(last_id):
    """Point `tabSeries` at the last id handed out, so the first name the new `autoname`
    produces is the one the sequence would have produced.

    Nothing to do for an empty table — a fresh series starts at 1 on its own.
    """
    if not last_id:
        return

    current = frappe.db.sql("select current from `tabSeries` where name = %s", (WORKBOOK_SERIES_KEY,))
    if not current:
        frappe.db.sql(
            "insert into `tabSeries` (name, current) values (%s, %s)",
            (WORKBOOK_SERIES_KEY, last_id),
        )
    elif cint(current[0][0]) < last_id:
        frappe.db.sql(
            "update `tabSeries` set current = %s where name = %s",
            (last_id, WORKBOOK_SERIES_KEY),
        )
