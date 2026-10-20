import frappe
from frappe.query_builder import Case
from frappe.query_builder.functions import IfNull
from frappe.utils import create_batch

from insights.upgrade import add_item

CHART = "Insights Chart v3"
QUERY = "Insights Query v3"
ALERT = "Insights Alert"
REFERENCE = "Insights Query Reference"
FOLDER = "Insights Folder"
EXECUTION_LOG = "Insights Query Execution Log"
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
    names it: no surface lists a cache in the query picker, so this should not
    happen, and the delete is permanent, so the chart's own field is read rather
    than trusted. The last is an alert that names it, set on the chart's rows
    back when they were a query a user could pick. The alert still fires on the
    rows the document returns, so the document stays as a query of its own, and
    the alert's owner is told it no longer follows the chart. A document kept
    for any of these is no longer the chart's: its column is cleared.

    The rows are deleted in batches, not through `frappe.delete_doc`. A site can
    hold thousands of caches, and `delete_doc` enqueues a job per document. Those
    jobs land together when the patch commits, so every enqueue after it, on this
    site and every site sharing the bench's queue, raises `QueueOverloaded` until
    a worker drains them. So this does the query controller's `on_trash` and
    Frappe's cleanup itself. A cache has no attachments to remove: nothing ever
    opened one in the desk.

    Running this twice deletes nothing the second time: the charts still hold
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

    repoint_charts_reading_their_own_cache()
    charted = (
        set(frappe.get_all(CHART, filters={"query": ("in", cached)}, pluck="query")) if cached else set()
    )
    cached = [name for name in cached if name not in charted]

    alerts = (
        frappe.get_all(ALERT, filters={"query": ("in", cached)}, fields=["name", "title", "query", "owner"])
        if cached
        else []
    )
    alerted = {alert.query for alert in alerts}
    cached = [name for name in cached if name not in alerted]

    for alert in alerts:
        report_alert(alert)
    title_after_charts(sourced | charted | alerted)
    unlink_from_charts(sourced | charted | alerted)
    if not cached:
        return

    folders = frappe.get_all(
        QUERY, filters={"name": ("in", cached), "folder": ("is", "set")}, pluck="folder", distinct=True
    )

    log_runs_under_chart_queries(cached)
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
    for name in sorted(alerted):
        print(f"  kept {name}: an alert watches it")


def repoint_charts_reading_their_own_cache() -> None:
    """Point a chart whose query is its own cache at the query the cache reads.

    Such a chart showed the cache's rows. Derived from the cache, it would
    apply its config a second time, to columns the first pass already
    summarized. The cache is its source query with the chart's config applied,
    so the chart derives the same rows from that source.
    """
    Chart = frappe.qb.DocType(CHART)
    for chart, cache in (
        frappe.qb.from_(Chart).select(Chart.name, Chart.query).where(Chart.query == Chart[FIELD]).run()
    ):
        operations = frappe.parse_json(frappe.db.get_value(QUERY, cache, "operations")) or []
        table = (operations[0].get("table") or {}) if operations else {}
        source = table.get("query_name") if table.get("type") == "query" else None
        if source and source != cache and frappe.db.exists(QUERY, source):
            frappe.db.set_value(CHART, chart, "query", source, update_modified=False)


def log_runs_under_chart_queries(cached: list[str]) -> None:
    """Move each cache's execution logs to its chart's query.

    A chart's runs were logged under its cache. The data store's weekly cleanup
    reads the logs to find the tables no query has read lately, and a log that
    names a deleted query reads nothing. So without this, a stored table only
    dashboards read is dropped on the first cleanup after the upgrade.
    """
    Chart = frappe.qb.DocType(CHART)
    Log = frappe.qb.DocType(EXECUTION_LOG)
    for batch in create_batch(cached, BATCH):
        query_of = dict(
            frappe.qb.from_(Chart)
            .select(Chart[FIELD], Chart.query)
            .where(Chart[FIELD].isin(batch) & (IfNull(Chart.query, "") != ""))
            .run()
        )
        if not query_of:
            continue
        case = Case()
        for cache, query in query_of.items():
            case = case.when(Log.query == cache, query)
        frappe.qb.update(Log).set(Log.query, case).where(Log.query.isin(list(query_of))).run()


def title_after_charts(kept: set[str]) -> None:
    """Give each kept cache with no title its chart's, so it is not a blank row
    in the workbook's query list."""
    for cache in (
        frappe.get_all(
            QUERY, filters={"name": ("in", sorted(kept)), "title": ("is", "not set")}, pluck="name"
        )
        if kept
        else []
    ):
        frappe.db.set_value(QUERY, cache, "title", chart_title(cache) or cache, update_modified=False)


def unlink_from_charts(kept: set[str]) -> None:
    """Clear the column on the charts whose cache is kept, so the document is a
    query of its own and a later run never takes it for a cache."""
    Chart = frappe.qb.DocType(CHART)
    for batch in create_batch(sorted(kept), BATCH):
        frappe.qb.update(Chart).set(Chart[FIELD], None).where(Chart[FIELD].isin(batch)).run()


def chart_title(cache: str) -> str | None:
    """The title of the chart that cached its query in `cache`."""
    Chart = frappe.qb.DocType(CHART)
    titles = frappe.qb.from_(Chart).select(Chart.title).where(Chart[FIELD] == cache).limit(1).run(pluck=True)
    return titles[0] if titles else None


def report_alert(alert) -> None:
    add_item(
        "J1",
        f'"{alert.title}" on chart "{chart_title(alert.query) or alert.query}"',
        reference=(QUERY, alert.query),
        user=None if alert.owner == "Administrator" else alert.owner,
    )


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
