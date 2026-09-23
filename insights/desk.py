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
docname a site stores stays the right one, and `rename_doc` carries a Link when
a workbook is made standard. A Link also refuses the delete of what it names:
taking the claim off instead would hand the desk document back to the
placeholder definition its author filled in to save the form. A re-sync that
drops a claimed member keeps it until nothing claims it
(`_delete_dropped_members`, `delete_unclaimed_kept_members`). A workbook its app
stopped shipping goes whole, as any unshipped standard document does, so a claim
never blocks a migrate, and the migrate names each claim it leaves dangling
(`report_dangling_claims`).

A claim decides who draws, never who may read. The desk document's own
permission already gated the load, and the island draws its own not-permitted
state for the Insights content behind it. So there is no permission check here:
one route must not behave like two different routes for two readers.
"""

import click
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from insights.hooks import insights_path

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


def boot_app_path(bootinfo) -> None:
    """Tell a desk page where this site mounts the Insights app.

    Every link an island offers is built out of it - the dashboard island's
    Edit action, a chart's own page, the workbook behind a card - and the host
    page is desk's, not the SPA's. The app's own www page carries the value in
    its page boot; a desk page has nothing but this.

    `insights.hooks.insights_path` is where the path is decided, once, from
    site config.
    """
    bootinfo.insights_path = f"/{insights_path}"


def claim(doc, method=None) -> None:
    """Name the island that draws `doc`, when Insights draws it.

    Both `doc_events` handlers name this one method. The doctype it was called
    for is on the document, so a per-doctype entry point would only be a second
    name for the same lookup.
    """
    island = island_for(doc)
    if island:
        doc.set_onload("island", island)


def claims_on(doctype: str, filters: dict) -> list[tuple[str, str, str]]:
    """The desk documents that claim a `doctype` document matching `filters`, as
    `(desk doctype, desk name, the claimed document's name)`."""
    claims = []
    for desk_doctype, field in DESK_ISLANDS.items():
        if field["options"] != doctype:
            continue
        names = frappe.get_all(doctype, filters=filters, pluck="name")
        if names:
            claims += [
                (desk_doctype, row.name, row.claimed)
                for row in frappe.get_all(
                    desk_doctype,
                    filters={field["fieldname"]: ("in", names)},
                    fields=["name", f"{field['fieldname']} as claimed"],
                )
            ]
    return claims


def dangling_claims() -> list[tuple[str, str, str]]:
    """The desk documents that claim a document that no longer exists, as
    `(desk doctype, desk name, the claimed document's name)`."""
    claims = []
    for desk_doctype, field in DESK_ISLANDS.items():
        rows = frappe.get_all(
            desk_doctype,
            filters={field["fieldname"]: ("is", "set")},
            fields=["name", f"{field['fieldname']} as claimed"],
        )
        existing = set(
            frappe.get_all(
                field["options"], filters={"name": ("in", [row.claimed for row in rows])}, pluck="name"
            )
            if rows
            else []
        )
        claims += [(desk_doctype, row.name, row.claimed) for row in rows if row.claimed not in existing]
    return claims


def report_dangling_claims() -> None:
    """Name, to whoever runs the migrate, each desk document left claiming
    Insights content that no longer exists, so they can clear its field."""
    for desk_doctype, desk_name, claimed in dangling_claims():
        click.secho(
            f"{desk_doctype} {desk_name} links {claimed}, which no longer exists. "
            f"Clear its {DESK_ISLANDS[desk_doctype]['label']} field.",
            fg="yellow",
        )


def refuse_delete_while_claimed(title: str, claims: list[tuple[str, str, str]]) -> None:
    """Refuse a delete while a desk document draws what it would take, naming
    that document. Asked before the delete changes anything: frappe's own link
    check comes after `on_trash`, and a refusal there leaves every change the
    hook made to whoever commits next."""
    if not claims:
        return

    frappe.throw(
        frappe._("Cannot delete {0} because {1} draw from it.").format(
            frappe.bold(title),
            ", ".join(
                f"{frappe._(doctype)} {frappe.utils.get_link_to_form(doctype, name)}"
                for doctype, name, _ in claims
            ),
        ),
        frappe.LinkExistsError,
    )


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
