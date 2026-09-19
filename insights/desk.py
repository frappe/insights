# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""How Insights draws a desk `Dashboard` and a desk `Dashboard Chart`.

Framework offers the seam: a desk document whose `__onload.island` names an
island is drawn by that island, and desk draws the document itself while the key
is absent. An app sets the key from its own `onload` handler, so what makes a
desk document ours is this module's choice, and it is one Custom Field per
doctype holding a link to the Insights content.

The field is a real `Link`, not a name in a `Data` field, because standard
content sync updates a shipped document in place and never re-keys it, so a
docname a site stores stays the right one. Sync also deletes with `force=True`,
so a link from desk can never block a re-sync.

A claim decides who draws, never who may read. The desk document's own
permission already gated the load, and the island draws its own not-permitted
state for the Insights content behind it. So there is no permission check here:
one route must not behave like two different routes for two readers.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# desk doctype -> the Custom Field that points it at Insights content, and the
# island that then draws it. One entry is the whole of a desk doctype's
# involvement, so a third one is a row here and a line in `hooks.py`.
DESK_ISLANDS = {
    "Dashboard": {
        "fieldname": "insights_dashboard",
        "label": "Insights Dashboard",
        "options": "Insights Dashboard v3",
        "insert_after": "dashboard_name",
        "island": "insights.dashboard",
        "prop": "dashboard",
    },
    "Dashboard Chart": {
        "fieldname": "insights_chart",
        "label": "Insights Chart",
        "options": "Insights Chart v3",
        "insert_after": "chart_name",
        "island": "insights.chart",
        "prop": "chart",
    },
}


def claim(doc, method=None) -> None:
    """Name the island that draws `doc`, when Insights draws it.

    Both `doc_events` handlers name this one method. The doctype it was called
    for is on the document, so a per-doctype entry point would only be a second
    name for the same lookup.
    """
    island = island_for(doc)
    if island:
        doc.set_onload("island", island)


def island_for(doc) -> dict | None:
    """The `__onload.island` value for `doc`, or None if Insights does not draw it."""
    field = DESK_ISLANDS.get(doc.doctype)
    if not field:
        return None

    reference = doc.get(field["fieldname"])
    if not reference:
        return None

    return {"name": field["island"], "props": {field["prop"]: reference}}


def install_custom_fields() -> None:
    """Add the fields a desk document claims Insights content with.

    Idempotent, and run on every migrate: the fields are ours on doctypes that
    are not, so nothing else puts them back if a site loses them.
    """
    create_custom_fields(
        {
            doctype: [
                {
                    "fieldname": field["fieldname"],
                    "label": field["label"],
                    "fieldtype": "Link",
                    "options": field["options"],
                    "insert_after": field["insert_after"],
                }
            ]
            for doctype, field in DESK_ISLANDS.items()
        }
    )
