# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""How Insights renders a desk `Dashboard`, `Dashboard Chart` and `Number Card`.

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

A claim decides who renders. Who may read is the desk document's own
permission, which already checked the load, and the island shows its own Not
Permitted state for the Insights content. A permission check in `claim` would
make one desk page render differently for two readers. A document Show in Desk
makes is the exception: only the chart's readers see it (`has_permission`).
"""

import os

import click
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import get_url_to_form

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
        "folder": "{module}_dashboard",
        "island": "insights.dashboard",
        "prop": "dashboard",
    },
    "Dashboard Chart": {
        "fieldname": "insights_chart",
        "label": "Insights Chart",
        "options": "Insights Chart v3",
        "insert_after": "chart_name",
        "folder": "dashboard_chart",
        "island": "insights.chart",
        "prop": "chart",
    },
    "Number Card": {
        "fieldname": "insights_chart",
        "label": "Insights Chart",
        "options": "Insights Chart v3",
        "insert_after": "label",
        "folder": "number_card",
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

    Every `doc_events` handler calls this one method. The document includes its
    doctype, so a per-doctype entry point would only add a second name.
    """
    island = island_for(doc)
    if island:
        doc.set_onload("island", island)


def show_in_desk(chart) -> dict:
    """The user adds the desk document to workspaces and dashboards with desk's
    own tools.

    A document that already shows the chart is reused, so a second click opens
    it instead of adding a copy. The search runs with the caller's permission,
    and a document they cannot read is not theirs to open.
    """
    chart = frappe.get_doc(chart.doctype, chart.name)
    doctype = desk_doctype(chart)
    fieldname = DESK_ISLANDS[doctype]["fieldname"]
    name = next(iter(frappe.get_list(doctype, filters={fieldname: chart.name}, pluck="name", limit=1)), None)
    if not name:
        doc = frappe.get_doc({"doctype": doctype, fieldname: chart.name, **desk_definition(doctype, chart)})
        name = doc.insert().name
    return {"doctype": doctype, "name": name, "url": get_url_to_form(doctype, name)}


def desk_doctype(chart) -> str:
    return "Number Card" if chart.chart_type == "Number" else "Dashboard Chart"


def can_show_in_desk(chart) -> bool:
    """Whether the caller may create the desk document Show in Desk makes for
    `chart`. Desk grants create to System Manager and Dashboard Manager."""
    return bool(frappe.has_permission(desk_doctype(chart), "create"))


def desk_definition(doctype: str, chart) -> dict:
    """The fields desk requires before it saves a `doctype`, though the island
    renders it.

    Desk shows a Dashboard Chart or Number Card to whoever may read its
    `document_type`. Counting Insights charts marks the document as one Show in
    Desk made, and `has_permission` narrows it to the chart's readers.
    """
    title = chart.title or chart.name
    if doctype == "Number Card":
        return {
            "label": title,
            "type": "Document Type",
            "document_type": chart.doctype,
            "function": "Count",
            "filters_json": "[]",
        }
    return {
        "chart_name": append_number_if_name_exists(doctype, title, "chart_name"),
        "chart_type": "Count",
        "document_type": chart.doctype,
        "based_on": "creation",
        "filters_json": "[]",
    }


def has_permission(doc, ptype, user) -> bool:
    """Refuse a desk document that Show in Desk made to whoever may not read
    its chart. Frappe's own rule for the doctype still applies.

    Only a document that counts Insights charts is narrowed. One claimed by
    hand counts what its author chose, and is read by the readers of that.
    """
    from insights.permissions import has_doc_permission

    chart = shown_chart(doc)
    return not chart or bool(has_doc_permission(chart, "read", user))


def get_permission_query_conditions(user, doctype) -> str:
    """`has_permission` for a list."""
    from insights.permissions import get_permission_query_conditions

    field = DESK_ISLANDS[doctype]
    readable = get_permission_query_conditions(user, field["options"])
    if not readable:
        return ""
    table = f"`tab{doctype}`"
    claim = f"{table}.`{field['fieldname']}`"
    return (
        f"(coalesce({table}.`document_type`, '') != {frappe.db.escape(field['options'])}"
        f" or coalesce({claim}, '') = ''"
        f" or {claim} not in (select `name` from `tab{field['options']}` where not {readable}))"
    )


def shown_chart(doc) -> frappe._dict | None:
    """The chart a desk document shows, if it counts Insights charts as
    `desk_definition` makes it."""
    field = DESK_ISLANDS[doc.doctype]
    if doc.get("document_type") == field["options"] and doc.get(field["fieldname"]):
        return frappe._dict(doctype=field["options"], name=doc.get(field["fieldname"]))


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
    are not, so nothing else restores them if a site loses them. Their module is
    Insights, so removing the app removes them. A field left behind links a
    doctype that no longer exists, and the desk document it sits on fails to load.
    """
    new = [
        doctype
        for doctype, field in DESK_ISLANDS.items()
        if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]})
    ]
    create_custom_fields(
        {
            doctype: [
                {
                    "fieldname": field["fieldname"],
                    "label": field["label"],
                    "fieldtype": "Link",
                    "options": field["options"],
                    "insert_after": field["insert_after"],
                    "module": "Insights",
                }
            ]
            for doctype, field in DESK_ISLANDS.items()
        }
    )
    for doctype in new:
        fill_shipped_claims(doctype)


def fill_shipped_claims(doctype: str) -> None:
    """Set the claims that the installed apps' `doctype` files carry.

    A file imported before the field existed lost its claim, and an unchanged
    file is never imported again.
    """
    fieldname = DESK_ISLANDS[doctype]["fieldname"]
    for path in shipped_files(doctype):
        doc = frappe.get_file_json(path)
        if doc.get(fieldname) and frappe.db.exists(doctype, doc.get("name")):
            frappe.db.set_value(doctype, doc["name"], fieldname, doc[fieldname], update_modified=False)


def shipped_files(doctype: str) -> list[str]:
    """The `<name>/<name>.json` files that `sync_dashboards` imports for `doctype`."""
    folder = DESK_ISLANDS[doctype]["folder"]
    paths = []
    for app in frappe.get_installed_apps():
        for module in frappe.local.app_modules.get(app) or []:
            path = frappe.get_module_path(module, folder.format(module=module))
            for name in os.listdir(path) if os.path.isdir(path) else []:
                if os.path.isfile(file := os.path.join(path, name, f"{name}.json")):
                    paths.append(file)
    return paths
