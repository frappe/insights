# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Export: documents back into an app's bundle files, the inverse of sync.

`bundles.py` reads an app's files and writes documents, on every site that
installs the app. This module reads a developer's own documents and writes the
files, once, on the bench where the content was authored. The blessed release
path is author in the builder -> export into the app repo -> git review ->
normal app release, so both halves of the round trip live on a developer bench
and nowhere else.

Export takes a dashboard's closure — the dashboard, the charts its items name,
and the queries those charts read, including each chart's `data_query` and any
query a query reads — writes one JSON file per item, and flags the documents
standard. It then runs sync over the app it exported into. That last step is
the point: after export the site's documents *are* the app's standard
documents, so they have to sit where a fresh install would put them (the
bundle's container workbook, references resolved, item keys as shipped). Sync
is what knows all of that, and running it means export never learns it twice.
The invariant to hold on to is that a second `sync_bundles()` straight after an
export changes nothing.

A file carries only `CARRIED_FIELDS`, with references as logical names and
nothing site-local: no `modified`, no `owner`, no docnames, no cached results,
no grid bookkeeping. Serialization is canonical (sorted keys, one indent
level), so re-exporting untouched content reproduces the file byte for byte and
a diff is only ever a real edit.

`write_back` closes the loop the other way: on a developer bench a standard
document is editable in the builder, and saving one writes its JSON back to the
file it came from — through the same serializer, so a builder save shows up in
git as the edit and nothing else.
"""

import json
import os
import re
from dataclasses import asdict, dataclass, field

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.model.document import Document
from frappe.utils import cint
from frappe.website.utils import cleanup_page_name

from insights.bundles import (
    BUNDLE_DIR,
    CARRIED_FIELDS,
    CHART,
    CHILD_FIELDS,
    DASHBOARD,
    FORMAT_VERSION,
    ITEM_TYPES,
    JSON_FIELDS,
    LINK_COLUMN,
    MANIFEST,
    NAME_PATTERN,
    QUERY,
    BundleError,
    SyncReport,
    dashboard_closure,
    discover_bundles,
    sync_app_bundles,
)

# the whole of a dashboard item's layout the format carries. A grid leaves
# bookkeeping of its own behind (`moved`), which is neither content nor stable.
LAYOUT_FIELDS = ("i", "x", "y", "w", "h")


@dataclass
class ExportReport:
    """What one export did — the items it wrote, and the sync that adopted them."""

    app: str
    bundle: str
    items: list[dict] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    sync: SyncReport | None = None

    @property
    def logical_ids(self) -> list[str]:
        return [item["logical_id"] for item in self.items]

    def as_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ export


def export_dashboard(
    dashboard: str, app: str, bundle: str | None = None, bundle_title: str | None = None
) -> ExportReport:
    """Write a dashboard's closure into `app`'s bundle and flag it standard.

    `bundle` is the folder inside the app's `insights/` directory; it defaults
    to the dashboard's own logical name. An item that already lives in one of
    the app's bundles is rewritten where it is — a bundle is organization, and
    export is not the place to reorganize.
    """
    _require_developer_mode()
    _require_installed(app)

    docs = dashboard_closure(dashboard)
    for doc in docs:
        doc.check_permission("write")

    names = _assign_names(app, docs)
    bundle = bundle or names[(DASHBOARD, docs[-1].name)]
    _check_name(bundle, "bundle folder")

    report = ExportReport(app, bundle)
    _write_manifest(app, bundle, bundle_title, report)

    def name_of(doctype: str, docname: str) -> str:
        name = names.get((doctype, str(docname)))
        if not name:
            raise BundleError(
                _("{0} {1} is referenced by this dashboard but is not part of what it exports").format(
                    doctype, docname
                )
            )
        return name

    for doc in docs:
        name = names[(doc.doctype, doc.name)]
        path = _item_path(app, doc.doctype, name, bundle)
        _write(path, dumps(serialize(doc, name_of)), report)
        report.items.append(
            {
                "doctype": doc.doctype,
                "docname": doc.name,
                "logical_id": f"{app}/{name}",
                "path": os.path.relpath(path, frappe.get_app_path(app)),
            }
        )
        # flagged by hand, not through the document: this is identity the
        # bundle owns, and writing it must not touch `modified` — the very
        # field the files are kept clean of
        frappe.db.set_value(
            doc.doctype,
            doc.name,
            {"logical_id": f"{app}/{name}", "is_standard": 1},
            update_modified=False,
        )

    # and now the site holds them the way an install would: in the bundle's
    # container workbook, references resolved, item keys as shipped
    report.sync = sync_app_bundles(app)
    return report


def _require_developer_mode() -> None:
    if not frappe.conf.developer_mode:
        frappe.throw(
            _("Exporting to an app needs a developer-mode bench."),
            title=_("Not a developer bench"),
        )


def _require_installed(app: str) -> None:
    if app not in frappe.get_installed_apps():
        frappe.throw(_("{0} is not installed on this site.").format(app))


# ------------------------------------------------------------ logical names


def _assign_names(app: str, docs: list[Document]) -> dict[tuple[str, str], str]:
    """A logical name per document, keyed by (doctype, docname).

    A name is derived from the title, kept to what a logical id, a slug and a
    file name all accept, and assigned once: a document that already carries a
    logical id keeps that name forever, because the id is what every consumer
    outside Insights holds on to. Within an app the namespace is flat, so a name
    something else already claims gets a numbered suffix.
    """
    taken = _taken_names(app, docs)
    names: dict[tuple[str, str], str] = {}

    # charts before their queries: a chart's `data_query` has no title of its
    # own (the controller mints it empty), so it is named after the chart
    owners = {str(doc.data_query): doc for doc in docs if doc.doctype == CHART and doc.data_query}
    for doc in sorted(docs, key=lambda d: list(ITEM_TYPES.values()).index(d.doctype), reverse=True):
        assigned = _existing_name(doc)
        if not assigned:
            base = _base_name(doc, owners, names)
            assigned = base if base not in taken else _suffixed(base, taken)
        taken.add(assigned)
        names[(doc.doctype, doc.name)] = assigned
    return names


def _existing_name(doc: Document) -> str | None:
    name = (doc.get("logical_id") or "").split("/", 1)
    return name[1] if len(name) == 2 and NAME_PATTERN.match(name[1] or "") else None


def _base_name(doc: Document, owners: dict[str, Document], names: dict) -> str:
    owner = owners.get(doc.name)
    if owner is not None and not doc.get("title"):
        return f"{names[(CHART, owner.name)]}_data"
    return _scrub(doc.get("title")) or _folder_of(doc.doctype)


def _scrub(title: str | None) -> str:
    name = cleanup_page_name(title or "")
    name = re.sub(r"[^a-z0-9_-]", "-", name).strip("-_")
    name = re.sub(r"-{2,}", "-", name)
    return name if NAME_PATTERN.match(name or "") else ""


def _suffixed(base: str, taken: set[str]) -> str:
    number = 2
    while f"{base}-{number}" in taken:
        number += 1
    return f"{base}-{number}"


def _taken_names(app: str, docs: list[Document]) -> set[str]:
    """Every logical name the app has already spoken for — on disk and on the
    site — less the ones the documents being exported hold themselves."""
    taken = {item.name for bundle in discover_bundles(app) for item in bundle.items}
    for doctype in ITEM_TYPES.values():
        for logical_id in frappe.get_all(
            doctype,
            filters={"is_standard": 1, "logical_id": ("like", f"{app}/%")},
            pluck="logical_id",
        ):
            taken.add(logical_id.split("/", 1)[1])
    return taken - {name for doc in docs if (name := _existing_name(doc))}


def _folder_of(doctype: str) -> str:
    return next(folder for folder, dt in ITEM_TYPES.items() if dt == doctype)


def _check_name(name: str, what: str) -> None:
    if not NAME_PATTERN.match(name or ""):
        frappe.throw(_("A {0} must be lowercase letters, digits, '-' or '_': got '{1}'").format(what, name))


# ----------------------------------------------------------- serialization


def serialize(doc: Document, name_of) -> dict:
    """One document as the file that ships it.

    Only `CARRIED_FIELDS`, all of them, always: a bundle file is the whole of
    what the format carries, not a delta, so a flag a vendor clears reaches the
    sites that already have it set. `name_of` turns a docname into the logical
    name that stands in for it — the only form a file may hold.
    """
    data: dict = {}
    for fieldname in CARRIED_FIELDS[doc.doctype]:
        if fieldname in CHILD_FIELDS:
            data[fieldname] = _child_rows(doc, fieldname)
        elif fieldname in JSON_FIELDS:
            data[fieldname] = _json_field(doc, fieldname, name_of)
        elif doc.doctype == CHART and fieldname in ("query", "data_query"):
            data[fieldname] = name_of(QUERY, doc.get(fieldname)) if doc.get(fieldname) else ""
        else:
            data[fieldname] = _scalar(doc, fieldname)
    return data


def dumps(data: dict) -> str:
    """The canonical form: sorted keys, one space of indent, a trailing
    newline. Content decides the bytes and nothing else does, so re-exporting
    untouched content reproduces the file exactly and a diff is a real edit."""
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def _scalar(doc: Document, fieldname: str):
    value = doc.get(fieldname)
    field = doc.meta.get_field(fieldname)
    if field and field.fieldtype in ("Check", "Int"):
        return cint(value)
    return value if value is not None else ""


def _child_rows(doc: Document, fieldname: str):
    rows = doc.get(fieldname) or []
    if fieldname == "visible_to_roles":
        # a role table reads better in a file as a plain list of role names
        return [row.role for row in rows]

    field = doc.meta.get_field(fieldname)
    keys = [f.fieldname for f in frappe.get_meta(field.options).fields if f.fieldtype not in no_value_fields]
    return [{key: row.get(key) for key in keys} for row in rows]


def _json_field(doc: Document, fieldname: str, name_of):
    value = frappe.parse_json(doc.get(fieldname) or ("{}" if fieldname == "config" else "[]"))
    if fieldname == "operations":
        return _export_operations(value, name_of)
    if fieldname == "items":
        return _export_items(value, name_of)
    return value


def _export_operations(operations, name_of):
    def walk(node):
        if isinstance(node, dict):
            if node.get("query_name"):
                node["query_name"] = name_of(QUERY, node["query_name"])
                if "workbook" in node:
                    # site state riding along in the operations: sync repoints
                    # it at the container workbook, so a file holds a placeholder
                    node["workbook"] = 0
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(operations)
    return operations


def _export_items(items, name_of):
    """A dashboard's items, references logical and every item keyed.

    The key is `layout.i`, the identity the grid already gives an item, made
    the vendor's: derived from what the item names, so it reads in a diff, is
    the same on every site that installs the bundle, and comes back the same on
    the next export. A text block names nothing, so its key is positional — it
    is also the one item type nothing ever references.
    """
    exported = []
    keys: set[str] = set()
    for index, entry in enumerate(items, start=1):
        entry = dict(entry)
        base = f"{entry.get('type') or 'item'}-{index}"

        if entry.get("type") == "chart" and entry.get("chart"):
            entry["chart"] = name_of(CHART, entry["chart"])
            base = f"chart-{entry['chart']}"

        if entry.get("type") == "filter":
            base = f"filter-{_scrub(entry.get('filter_name')) or index}"
            entry["links"] = _export_links(entry.get("links"), name_of)

        key = base if base not in keys else _suffixed(base, keys)
        keys.add(key)
        entry["layout"] = _export_layout(entry.get("layout"), key)
        exported.append(entry)
    return exported


def _export_links(links, name_of) -> dict:
    exported = {}
    for chart, column in (links or {}).items():
        match = LINK_COLUMN.match(column or "")
        if not match:
            # sync drops a link it cannot read; a file that kept one would put
            # the document and its file permanently out of step
            continue
        query, column_name = match.groups()
        exported[name_of(CHART, chart)] = f"`{name_of(QUERY, query)}`.`{column_name}`"
    return exported


def _export_layout(layout, key: str) -> dict:
    layout = layout or {}
    exported = {field: layout[field] for field in LAYOUT_FIELDS if field in layout}
    exported["i"] = key
    return exported


# ------------------------------------------------------------------- files


def _write_manifest(app: str, bundle: str, title: str | None, report: ExportReport) -> None:
    path = os.path.join(_bundle_path(app, bundle), MANIFEST)
    if os.path.isfile(path):
        # an existing bundle's manifest is the vendor's: its title and its
        # required apps are decisions export has no business revisiting
        return
    manifest = {
        "title": title or bundle.replace("_", " ").replace("-", " ").title(),
        "required_apps": [],
        "format_version": FORMAT_VERSION,
    }
    _write(path, dumps(manifest), report)


def _item_path(app: str, doctype: str, name: str, bundle: str) -> str:
    return _existing_file(app, doctype, name) or os.path.join(
        _bundle_path(app, bundle), _folder_of(doctype), f"{name}.json"
    )


def _bundle_path(app: str, bundle: str) -> str:
    return os.path.join(frappe.get_app_path(app, BUNDLE_DIR), bundle)


def _existing_file(app: str, doctype: str, name: str) -> str | None:
    """Where the app already ships this item, if it does. A bundle folder
    organizes, it does not identify, so an item that moved bundles by hand is
    rewritten where the developer put it."""
    root = frappe.get_app_path(app, BUNDLE_DIR)
    if not os.path.isdir(root):
        return None
    for folder in sorted(os.listdir(root)):
        path = os.path.join(root, folder, _folder_of(doctype), f"{name}.json")
        if os.path.isfile(path):
            return path
    return None


def _write(path: str, content: str, report: ExportReport | None = None) -> bool:
    """Write only a file that would change, so an export that changes nothing
    leaves even the timestamps alone."""
    if os.path.isfile(path):
        with open(path) as f:
            if f.read() == content:
                return False

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    if report is not None:
        report.written.append(path)
    return True


# -------------------------------------------------------------- write-back


def write_back(doc, method=None) -> bool:
    """A standard document saved on a developer bench, back into its file.

    The other half of the round trip: the builder is where shipped content is
    iterated on, and a save that did not reach the app folder would be a change
    the release never carries. Same serializer as export, so a save shows up in
    git as the edit and nothing else.

    Silent where there is nothing to write to — the document's app is not on
    this bench, or the file is gone. Export is what creates files; a save is
    not the moment to invent one.
    """
    if not frappe.conf.developer_mode:
        return False
    if doc.doctype not in ITEM_TYPES.values():
        return False
    if not doc.get("is_standard") or not doc.get("logical_id"):
        return False
    if doc.flags.in_bundle_sync or frappe.flags.in_bundle_sync:
        # sync wrote this document *from* the file it would write back to
        return False

    app, _sep, name = doc.logical_id.partition("/")
    if not name or app not in frappe.get_installed_apps():
        return False
    path = _existing_file(app, doc.doctype, name)
    if not path:
        return False

    try:
        content = dumps(serialize(doc, _shipped_name))
    except BundleError as e:
        # a reference to content the app does not ship: the document is ahead of
        # its bundle, and half a file is worse than a stale one
        message = _("{0} was not written back to {1}: {2}").format(doc.name, app, e)
        frappe.logger("insights").warning(message)
        frappe.msgprint(message, alert=True)
        return False

    return _write(path, content)


def _shipped_name(doctype: str, docname: str) -> str:
    logical_id = frappe.db.get_value(doctype, docname, "logical_id") if docname else None
    if not logical_id:
        raise BundleError(_("{0} {1} is not shipped by any app").format(doctype, docname))
    return logical_id.split("/", 1)[1]


# --------------------------------------------------------- export targets


def export_targets() -> dict:
    """The apps an export can go into, and the bundles they already ship —
    what an "Export to app…" dialog needs to offer, and whether it may."""
    apps = []
    for app in frappe.get_installed_apps():
        try:
            bundles = [{"folder": b.folder, "title": b.title} for b in discover_bundles(app)]
        except BundleError:
            # a bundle this bench cannot read is a problem for sync to report,
            # not a reason to hide the app from an export dialog
            bundles = []
        apps.append(
            {
                "app": app,
                "title": (frappe.get_hooks("app_title", app_name=app) or [app])[0],
                "bundles": bundles,
            }
        )
    return {"developer_mode": bool(frappe.conf.developer_mode), "apps": apps}
