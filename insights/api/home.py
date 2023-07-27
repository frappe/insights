# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe


@frappe.whitelist()
def create_last_viewed_log(record_type, record_name):
    recordToDoctype = {
        "Query": "Insights Query",
        "Dashboard": "Insights Dashboard",
        "NotebookPage": "Insights Notebook Page",
    }
    try:
        comment = frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Comment",
                "comment_email": frappe.session.user,
                "reference_doctype": recordToDoctype.get(record_type),
                "reference_name": record_name,
                "content": "Last Viewed",
            }
        )
        comment.insert(ignore_permissions=True)
    except BaseException:
        pass


@frappe.whitelist()
def get_last_viewed_records():
    Comment = frappe.qb.DocType("Comment")
    TRACKED_DOCTYPES = ["Insights Query", "Insights Dashboard", "Insights Notebook Page"]
    records = (
        frappe.qb.from_(Comment)
        .select(Comment.reference_doctype, Comment.reference_name, Comment.creation)
        .where(
            (Comment.comment_email == frappe.session.user)
            & Comment.reference_doctype.isin(TRACKED_DOCTYPES)
            & (Comment.comment_type == "Comment")
            & (Comment.content == "Last Viewed")
        )
        .orderby(Comment.creation, order=frappe.qb.desc)
        .groupby(Comment.reference_doctype, Comment.reference_name)
        .limit(10)
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
