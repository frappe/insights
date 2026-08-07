# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Duplicate to edit: the customization floor.

Standard content is read-only on a site, so taking a copy is the only way to
change a shipped dashboard. The copy is an ordinary user document — owned by
whoever asked for it, in a workbook of their own, editable — and it is never
handed back for the shipped Standard ID: the resolver keys that lookup on
`is_standard`, which a copy is not.

What is copied is the dashboard's closure: the dashboard, the charts its items
name, the queries those charts read and any query a query reads. That is the
same closure export writes into a bundle, so this uses that walk rather than
growing a second one.

Two entry points, one copy. `duplicate_dashboard` is what the island's overflow
offers on a single shipped dashboard; `duplicate_bundle` is what the gallery
offers on a whole bundle, which lands on a site as one container workbook. The
second is the first over every dashboard in the bundle, into one workbook.

The copy carries the `standard_id` it was made from. That is provenance and
nothing else — it says which shipped item this document started as, which is
what a real customization model (ticket 10) needs to line a fork up against the
original it drifted from.

Two things are deliberately not carried over the same way:

- **The audience does not come along.** A shipped `visibility` is the vendor's
  declaration about the original; a copy is the duplicator's own draft, so it
  starts at `Private` and is published, if ever, by its new owner. Duplicating
  is not a way to re-publish someone else's audience.
- **`data_authority` does come along, but the authority *user* changes.** The
  authority is how the content is meant to run, so it is copied as declared. The
  user it resolves to is the document owner (see `data_authority.py`), and the
  copy's owner is the duplicator — so an `Author` chart in a copy runs under the
  person who duplicated it, never under whoever owned the original. A copy can
  therefore never show rows its owner could not already reach.

The source is only ever read here. Nothing below saves a document it did not
create.
"""

import frappe
from frappe import _

from insights.bundles import (
    CARRIED_FIELDS,
    CHART,
    CHILD_FIELDS,
    DASHBOARD,
    LINK_COLUMN,
    QUERY,
    dashboard_closure,
)
from insights.resolver import ContentNotAvailableError, resolve_for_read

WORKBOOK = "Insights Workbook"
PRIVATE = "Private"


def duplicate_dashboard(reference: str) -> dict:
    """Copy a dashboard's closure into a new workbook the caller owns.

    `reference` is any form the resolver accepts, read-checked the same way
    every other consumer path reads content. The read on the dashboard is the
    whole check: its audience is what carries the charts on it, and the queries
    behind those charts are exactly what a viewer is never handed directly.

    Returns the workbook and the dashboard copy inside it — what it takes to
    open the copy in the builder.
    """
    name = resolve_for_read(DASHBOARD, reference)
    title = frappe.db.get_value(DASHBOARD, name, "title")

    workbook = _new_workbook(title or _("Dashboard"))
    copies: dict[tuple[str, str], str] = {}
    _copy_closure(name, workbook, copies)

    return {"workbook": workbook, "dashboard": copies[(DASHBOARD, name)]}


def duplicate_bundle(workbook: str) -> dict:
    """Copy a bundle's shipped dashboards into one workbook the caller owns.

    A bundle lands on a site as one container workbook, hence the argument. Same
    semantics as `duplicate_dashboard`, with one `copies` map across all of them
    so a query two dashboards read is copied once and shared.

    The read check is per dashboard, not on the workbook: a container is
    Administrator-owned and nobody's to read, while the audience the dashboards
    declare is what admits a viewer.
    """
    dashboards = frappe.get_list(
        DASHBOARD,
        filters={"workbook": workbook, "is_standard": 1},
        order_by="creation asc",
        pluck="name",
    )
    if not dashboards:
        frappe.throw(_("This content is not available"), exc=ContentNotAvailableError)

    copy = _new_workbook(frappe.db.get_value(WORKBOOK, workbook, "title") or _("Workbook"))
    copies: dict[tuple[str, str], str] = {}
    for dashboard in dashboards:
        _copy_closure(resolve_for_read(DASHBOARD, dashboard), copy, copies)

    return {"workbook": copy, "dashboard": copies[(DASHBOARD, dashboards[0])]}


def _new_workbook(title: str) -> str:
    workbook = frappe.new_doc(WORKBOOK)
    workbook.title = _("{0} (copy)").format(title)
    workbook.insert()
    return workbook.name


def _copy_closure(dashboard: str, workbook: str, copies: dict) -> None:
    """One dashboard's closure into `workbook`, recording what each copy became.

    `copies` is keyed by (doctype, docname). The closure comes back queries
    first, then charts, then the dashboard, so every reference is already copied
    when the document holding it is written — and an item already in the map
    (shared with a dashboard copied before it) is not copied twice.
    """
    for doc in dashboard_closure(dashboard):
        key = (doc.doctype, str(doc.name))
        if key not in copies:
            copies[key] = _copy(doc, workbook, copies)


def _copy(doc, workbook: str, copies: dict) -> str:
    """One document as the caller's own, references repointed at the copies.

    `CARRIED_FIELDS` is the whole of what comes across — the same set a bundle
    ships, which is content and only content. Everything else on the document is
    site-side (the workbook, folders, previews), derived by a controller (a
    dashboard's slug and linked charts), or identity, which this function
    decides.
    """
    copy = frappe.new_doc(doc.doctype)
    for fieldname in CARRIED_FIELDS[doc.doctype]:
        copy.set(fieldname, _value(doc, fieldname, workbook, copies))

    copy.workbook = workbook
    # what it was made from, without the standing that came with it
    copy.standard_id = doc.get("standard_id")
    copy.is_standard = 0
    copy.insert()
    return copy.name


def _value(doc, fieldname: str, workbook: str, copies: dict):
    if fieldname == "visibility":
        return PRIVATE
    if fieldname == "visible_to_roles":
        return []
    if fieldname in CHILD_FIELDS:
        return [row.as_dict(no_default_fields=True) for row in doc.get(fieldname) or []]
    if fieldname == "operations":
        return frappe.as_json(_operations(doc, workbook, copies))
    if fieldname == "items":
        return frappe.as_json(_items(doc, copies))
    if doc.doctype == CHART and fieldname == "query":
        return _copy_of(QUERY, doc.get(fieldname), copies) if doc.get(fieldname) else None

    return doc.get(fieldname)


def _operations(doc, workbook: str, copies: dict):
    """A query's operations, reading from the copies instead of the originals.

    The workbook id riding along beside a query reference is site state the
    builder puts there; it follows the copy into its new workbook.
    """

    def walk(node):
        if isinstance(node, dict):
            if node.get("query_name"):
                node["query_name"] = _copy_of(QUERY, node["query_name"], copies)
                if "workbook" in node:
                    node["workbook"] = workbook
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    operations = frappe.parse_json(doc.get("operations") or "[]")
    walk(operations)
    return operations


def _items(doc, copies: dict):
    """A dashboard's items, pointed at the copied charts and queries."""
    items = frappe.parse_json(doc.get("items") or "[]")
    for entry in items:
        if entry.get("type") == "chart" and entry.get("chart"):
            entry["chart"] = _copy_of(CHART, entry["chart"], copies)

        if entry.get("type") == "filter":
            entry["links"] = _links(entry.get("links"), copies)
    return items


def _links(links, copies: dict) -> dict:
    """Filter links, keeping only the ones the copy can honour.

    A link naming a chart that is not on the dashboard, or a query no chart on
    it reads, does nothing on the original either — it is left behind rather
    than carried as a reference into content it cannot reach.
    """
    copied = {}
    for chart, column in (links or {}).items():
        match = LINK_COLUMN.match(column or "")
        query = copies.get((QUERY, match.group(1))) if match else None
        target = copies.get((CHART, str(chart)))
        if query and target:
            copied[target] = f"`{query}`.`{match.group(2)}`"
    return copied


def _copy_of(doctype: str, docname, copies: dict) -> str:
    name = copies.get((doctype, str(docname)))
    if not name:
        # the closure is what the dashboard needs; a reference outside it means
        # the walk and this copy disagree, and half a copy is worse than none
        frappe.throw(_("{0} {1} is referenced by this dashboard but was not copied").format(doctype, docname))
    return name
