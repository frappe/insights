import frappe
from frappe.utils import create_batch

CHART = "Insights Chart v3"
QUERY = "Insights Query v3"
ALERT = "Insights Alert"
REFERENCE = "Insights Query Reference"
FOLDER = "Insights Folder"
FIELD = "data_query"

BATCH = 500

# What `frappe.delete_doc` removes beside a document's row, as (table, doctype
# column, name column). The first eight are its `delete_dynamic_links` job.
DELETED_REFERENCES = (
    ("ToDo", "reference_type", "reference_name"),
    ("Email Unsubscribe", "reference_doctype", "reference_name"),
    ("DocShare", "share_doctype", "share_name"),
    ("Version", "ref_doctype", "docname"),
    ("Comment", "reference_doctype", "reference_name"),
    ("View Log", "reference_doctype", "reference_name"),
    ("Document Follow", "ref_doctype", "ref_docname"),
    ("Notification Log", "document_type", "document_name"),
    ("Communication Link", "link_doctype", "link_name"),
    ("Tag Link", "document_type", "document_name"),
    ("__global_search", "doctype", "name"),
    ("__Auth", "doctype", "name"),
)

# What it unlinks rather than deletes, because the row is someone else's record.
CLEARED_REFERENCES = (
    ("Communication", "reference_doctype", "reference_name"),
    ("Activity Log", "reference_doctype", "reference_name"),
    ("Activity Log", "timeline_doctype", "timeline_name"),
)


def execute():
    """Delete the query documents charts cached their derived query in.

    A chart's rows come from a query derived from its config. That query used to
    be derived in the browser and written to a second query document the chart
    linked to. It is derived on the server at execution time now, so the field is
    gone and the documents behind it are caches nothing fills, reads or repairs.

    The charts still hold the docnames: dropping a field leaves its column, and
    only `bench trim-database` ever removes one. So this reads `data_query`
    straight off the table, checking the column is there rather than the field,
    and finds every cache whether it runs before the model sync or after.

    A cache is owned by one chart and referenced nowhere else, with three
    exceptions. One is a query that sources it: the edge table answers that,
    and such a document is left where it is. Another is a chart whose `query`
    names it: no surface offers a cache in the query picker, so this should not
    happen, and the delete is permanent, so the chart's own field is read rather
    than trusted. The last is an alert that may name it, set on the chart's rows
    back when they were a query a user could pick. The query controller already
    says an alert cannot outlive the query it watches, so the alert goes with
    the document. It could not have fired again either way, since nothing has
    maintained that document since the derivation moved.

    The rows are deleted in batches, not through `frappe.delete_doc`. A site can
    hold thousands of caches, and `delete_doc` enqueues a job per document. Those
    jobs land together when the patch commits, so every enqueue after it, on this
    site and every site sharing the bench's queue, raises `QueueOverloaded` until
    a worker drains them. So this does the query controller's `on_trash` and
    Frappe's cleanup itself. A cache has no attachments to remove: nothing ever
    opened one in the desk.

    Running this twice deletes nothing the second time: the charts still carry
    the docnames in the orphan column, and none of them name a document that is
    still there.
    """
    if FIELD not in frappe.db.get_table_columns(CHART):
        return

    cached = frappe.db.sql_list(
        f"select distinct `{FIELD}` from `tab{CHART}` where ifnull(`{FIELD}`, '') != ''"
    )
    cached = [name for name in cached if frappe.db.exists(QUERY, name)]
    if not cached:
        return

    # A cache is referenced nowhere else, so nothing checks links before the
    # delete. A cache another query sources is not a cache any more, and deleting
    # that one would break the query that reads it: it is named and left.
    sourced = set(
        frappe.get_all(
            REFERENCE,
            filters={"ref_type": "Query", "ref_query": ("in", cached)},
            pluck="ref_query",
        )
    )
    cached = [name for name in cached if name not in sourced]

    charted = (
        set(frappe.get_all(CHART, filters={"query": ("in", cached)}, pluck="query")) if cached else set()
    )
    cached = [name for name in cached if name not in charted]
    if not cached:
        return

    alerts = frappe.get_all(ALERT, filters={"query": ("in", cached)}, fields=["name", "title"])
    folders = frappe.get_all(
        QUERY, filters={"name": ("in", cached), "folder": ("is", "set")}, pluck="folder", distinct=True
    )

    delete_documents(ALERT, [alert.name for alert in alerts])
    for batch in create_batch(cached, BATCH):
        frappe.db.delete(REFERENCE, {"query": ("in", batch)})
        frappe.db.delete(REFERENCE, {"ref_query": ("in", batch)})
    delete_documents(QUERY, cached)
    delete_documents(FOLDER, empty_query_folders(folders))

    print(f"Insights: deleted {len(cached)} cached chart query document(s)")
    for name in sorted(sourced):
        print(f"  kept {name}: another query sources it")
    for name in sorted(charted):
        print(f"  kept {name}: a chart reads it")
    for alert in alerts:
        print(f"  deleted alert {alert.name} ({alert.title}) with its query")


def delete_documents(doctype: str, names: list[str]) -> None:
    """Delete the documents and what `frappe.delete_doc` would remove with them,
    in this transaction and without enqueueing anything."""
    child_tables = [field.options for field in frappe.get_meta(doctype).get_table_fields()]
    has_tag_links = frappe.db.table_exists("Tag Link")

    for batch in create_batch(names, BATCH):
        for table, doctype_column, name_column in DELETED_REFERENCES:
            if table == "Tag Link" and not has_tag_links:
                continue
            frappe.db.delete(table, {doctype_column: doctype, name_column: ("in", batch)})

        for table, doctype_column, name_column in CLEARED_REFERENCES:
            frappe.db.set_value(
                table,
                {doctype_column: doctype, name_column: ("in", batch)},
                {doctype_column: None, name_column: None},
                update_modified=False,
            )

        for child_table in child_tables:
            frappe.db.delete(child_table, {"parenttype": doctype, "parent": ("in", batch)})

        frappe.db.delete(doctype, {"name": ("in", batch)})


def empty_query_folders(folders: list[str]) -> list[str]:
    """The query folders left holding no query, which the query controller's
    `on_trash` deletes."""
    if not folders:
        return []
    return [
        folder
        for folder in frappe.get_all(FOLDER, filters={"name": ("in", folders), "type": "query"}, pluck="name")
        if not frappe.db.exists(QUERY, {"folder": folder})
    ]
