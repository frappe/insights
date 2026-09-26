# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""How Insights renders a desk `Dashboard` and a desk `Dashboard Chart`.

The framework renders a desk document with an island when its `__onload.island`
names one. Without the key, desk renders the document itself. Insights sets the
key from its `onload` handler. The claim is one Custom Field per doctype, a link
to the Insights content.

The field is a `Link`, not a `Data` field that holds a name. Standard content
sync updates a shipped document in place and never renames it, so a stored
docname stays valid. `rename_doc` updates a Link when a workbook is made
standard.

A Link also blocks the delete of the content it names. Clearing the claim
instead would make desk render the placeholder definition the author filled in
to save the form. A re-sync that drops a claimed member keeps it until nothing
claims it (`_delete_dropped_members`, `delete_unclaimed_kept_members`). A
workbook that its app no longer ships is deleted whole, like any unshipped
standard document, so a claim never blocks a migrate. The migrate lists each
claim it leaves dangling (`report_dangling_claims`).

A claim decides who renders, never who may read. The desk document's own
permission already checked the load. The island shows its own Not Permitted
state for the Insights content. A permission check here would make one desk
page render differently for two readers.
"""

import click
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from insights.hooks import insights_path

# desk doctype -> the Custom Field that links it to Insights content, and the
# island that renders it. Another desk doctype needs one entry here and one
# line in `hooks.py`.
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

    Islands build their links from it: the dashboard island's Edit action, a
    chart's own page, the workbook behind a card. The app's www page gets the
    value in its own boot. A desk page has only this.

    `insights.hooks.insights_path` reads the path from site config.
    """
    bootinfo.insights_path = f"/{insights_path}"


def claim(doc, method=None) -> None:
    """Set the island that renders `doc`, if Insights renders it.

    Both `doc_events` handlers call this one method. The document includes its
    doctype, so a per-doctype entry point would only add a second name.
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
    """Print each desk document that claims deleted Insights content, so
    whoever runs the migrate can clear its field."""
    for desk_doctype, desk_name, claimed in dangling_claims():
        click.secho(
            f"{desk_doctype} {desk_name} links {claimed}, which no longer exists. "
            f"Clear its {DESK_ISLANDS[desk_doctype]['label']} field.",
            fg="yellow",
        )


def refuse_delete_while_claimed(title: str, claims: list[tuple[str, str, str]]) -> None:
    """Refuse a delete while a desk document renders the content, and name that
    document. Call it before the delete changes anything. Frappe's own link
    check runs after `on_trash`, and a refusal there leaves the hook's changes
    for whoever commits next."""
    if not claims:
        return

    frappe.throw(
        frappe._("Cannot delete {0} because {1} use it.").format(
            frappe.bold(title),
            ", ".join(
                f"{frappe._(doctype)} {frappe.utils.get_link_to_form(doctype, name)}"
                for doctype, name, _ in claims
            ),
        ),
        frappe.LinkExistsError,
    )


def island_for(doc) -> dict | None:
    """The `__onload.island` value for `doc`, or None if Insights does not render it."""
    field = DESK_ISLANDS.get(doc.doctype)
    if not field:
        return None

    reference = doc.get(field["fieldname"])
    if not reference:
        return None

    return {"name": field["island"], "props": {field["prop"]: reference}}


def install_custom_fields() -> None:
    """Add the Custom Fields that link desk documents to Insights content.

    Idempotent, and run on every migrate. The fields are ours but the doctypes
    are not, so nothing else restores them if a site loses them.
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
