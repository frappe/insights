import frappe

from insights.bundles import bundle_sync

CHART = "Insights Chart v3"
QUERY = "Insights Query v3"
ALERT = "Insights Alert"
FIELD = "data_query"


def execute():
    """Delete the query documents charts cached their derived query in.

    A chart's rows come from a query derived from its config. That query used to
    be derived in the browser and written to a second query document the chart
    linked to; it is derived on the server at execution time now, so the field is
    gone and the documents behind it are caches nothing fills, reads or repairs.

    The charts still hold the docnames: dropping a field leaves its column, and
    only `bench trim-database` ever removes one. So this reads `data_query`
    straight off the table, checking the column is there rather than the field,
    and finds every cache whether it runs before the model sync or after.

    It runs after. Before the sync, a site's schema is still the previous
    release's — the field would be part of the doctype there, but any field the
    same release *adds* would not be a column yet, and loading a query document
    selects the whole of its meta. That is not hypothetical: run before the
    sync, this patch dies on `is_standard` on any site that has not migrated
    since bundles landed. The documents have to go through their controller,
    which is what takes an alert set on one and the query's reference edges with
    it, so the schema the controller expects has to be the one that is there.

    A cache is owned by one chart and referenced nowhere else, with one
    exception: an alert may name it, having been set on the chart's rows back
    when they were a query a user could pick. The query controller already says
    an alert cannot outlive the query it watches, so the alert goes with the
    document — and it could not have fired again either way, since nothing has
    maintained that document since the derivation moved.

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

    alerts = frappe.get_all(ALERT, filters={"query": ("in", cached)}, fields=["name", "title"])

    # shipped charts cache like any other, and their caches are standard content
    # this app is retiring — the same work as a sync, under a different trigger
    with bundle_sync():
        for name in cached:
            frappe.delete_doc(QUERY, name, force=True, ignore_permissions=True, delete_permanently=True)

    print(f"Insights: deleted {len(cached)} cached chart query document(s)")
    for alert in alerts:
        print(f"  alert {alert.name} ({alert.title}) watched one of them and went with it")
