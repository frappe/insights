import frappe

CHART = "Insights Chart v3"
QUERY = "Insights Query v3"
ALERT = "Insights Alert"
REFERENCE = "Insights Query Reference"
FIELD = "data_query"


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

    It runs after. Before the sync, a site's schema is still the previous
    release's: the field would be part of the doctype there, but any field the
    same release *adds* would not be a column yet, and loading a query document
    selects the whole of its meta. The documents have to go through their
    controller, which is what takes an alert set on one and the query's
    reference edges with it, so the schema the controller expects has to be the
    one that is there.

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

    # A cache is referenced nowhere else, so the delete goes through with the link
    # check forced. A cache another query sources is not a cache any more, and
    # forcing that one would break the query that reads it: it is named and left.
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

    alerts = (
        frappe.get_all(ALERT, filters={"query": ("in", cached)}, fields=["name", "title"]) if cached else []
    )

    for name in cached:
        frappe.delete_doc(QUERY, name, force=True, ignore_permissions=True, delete_permanently=True)

    print(f"Insights: deleted {len(cached)} cached chart query document(s)")
    for name in sorted(sourced):
        print(f"  kept {name}: another query sources it")
    for name in sorted(charted):
        print(f"  kept {name}: a chart reads it")
    for alert in alerts:
        print(f"  deleted alert {alert.name} ({alert.title}) with its query")
