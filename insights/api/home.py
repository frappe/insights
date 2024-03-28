# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from pypika.functions import Max


@frappe.whitelist()
def create_last_viewed_log(record_type, record_name):
    recordToDoctype = {
        "Query": "Insights Query",
        "Dashboard": "Insights Dashboard",
        "NotebookPage": "Insights Notebook Page",
    }
    try:
        doc = frappe.get_doc(recordToDoctype[record_type], record_name)
        doc.add_viewed(force=True)
    except Exception:
        pass


@frappe.whitelist()
def get_last_viewed_records():
    ViewLog = frappe.qb.DocType("View Log")
    TRACKED_DOCTYPES = ["Insights Query", "Insights Dashboard", "Insights Notebook Page"]
    records = (
        frappe.qb.from_(ViewLog)
        .select(
            ViewLog.reference_doctype,
            ViewLog.reference_name,
            Max(ViewLog.modified).as_("creation"),
        )
        .where(
            (ViewLog.viewed_by == frappe.session.user)
            & ViewLog.reference_doctype.isin(TRACKED_DOCTYPES)
        )
        .groupby(ViewLog.reference_doctype, ViewLog.reference_name)
        .orderby(Max(ViewLog.modified).as_("creation"), order=frappe.qb.desc)
        .limit(20)
        .run(as_dict=True)
    )
    fetch_titles(records)
    fetch_notebook_names(records)

    return records


def fetch_titles(records):
    docnames_by_doctype = {}
    for record in records:
        docnames_by_doctype.setdefault(record.reference_doctype, []).append(record.reference_name)

    for doctype, docnames in docnames_by_doctype.items():
        titles = frappe.get_all(
            doctype,
            filters={"name": ["in", docnames]},
            fields=["name", "title"],
        )
        for title in titles:
            for record in records:
                if record.reference_doctype == doctype and record.reference_name == title.name:
                    record["title"] = title.title
                    break


def fetch_notebook_names(records):
    docnames_by_doctype = {}
    for record in records:
        if record.reference_doctype == "Insights Notebook Page":
            docnames_by_doctype.setdefault(record.reference_doctype, []).append(
                record.reference_name
            )

    for doctype, docnames in docnames_by_doctype.items():
        notebooks = frappe.get_all(
            "Insights Notebook Page",
            filters={"name": ["in", docnames]},
            fields=["name", "notebook"],
        )
        for notebook in notebooks:
            for record in records:
                if record.reference_doctype == doctype and record.reference_name == notebook.name:
                    record["notebook"] = notebook.notebook
                    break
