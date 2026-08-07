# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Bundles: how an app ships analytics, and how a site reconciles them.

An app ships content as files under `<app>/insights/<bundle>/`, the folder
idiom Studio and Builder already use:

    erpnext/insights/selling/
        workbook.json                   title, required_apps, format_version
        query/monthly_sales.json
        chart/monthly_sales_by_item.json
        dashboard/sales_overview.json

One file is one document. The file name is the item's logical name, the folder
above it names the doctype, and `{app}/{name}` — the `logical_id` the resolver
looks up — is the identity. That namespace is flat per app: bundle folders
organize, they do not identify, so two bundles in one app may not ship the same
name. References inside the files (dashboard -> chart, chart -> query, query ->
query) are logical names; docnames are site-local hashes and never appear in a
bundle.

Sync reconciles those files into real documents on migrate. It is declarative:
the files are the truth, so a new file is created, a changed file is updated, and
a standard document whose file is gone is deleted. It is idempotent: a run that
finds nothing changed writes nothing, not even a `modified` timestamp. Documents
a site's users made are never touched — only `is_standard` documents are, and a
duplicate of shipped content is an ordinary user document.

The v3 builder is workbook-centric, so shipped documents need a workbook to
live in. `workbook.json` titles it and the folder identifies it, but the
workbook is still built site-side rather than reconciled from the file like
every other document here: sync keeps one Administrator-owned workbook per
bundle, carrying the bundle key as its `logical_id` — the same identity the
content doctypes carry (see `_container_workbook`). Making it the fourth
reconciled doctype is the next step of the reshape, not this one.
"""

import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cint
from frappe.website.utils import cleanup_page_name

QUERY = "Insights Query v3"
CHART = "Insights Chart v3"
DASHBOARD = "Insights Dashboard v3"

# the directory an app ships its bundles in, relative to its package
BUNDLE_DIR = "insights"

# the manifest is the workbook's file: a shipped folder is a workbook, so the
# file that titles it carries its name. Recognized under this name only — the
# format has no compatibility read, because nothing has shipped against it yet
# and this rename is why nothing may until it lands.
MANIFEST = "workbook.json"

# owned by Insights, append-only within a major: an importer tolerates keys it
# does not know, and refuses a bundle written for a later major
FORMAT_VERSION = 1

# item folder -> doctype, in dependency order. Creation follows this order and
# deletion reverses it, so a reference never dangles mid-sync.
ITEM_TYPES = {
    "query": QUERY,
    "chart": CHART,
    "dashboard": DASHBOARD,
}

# the fields a bundle carries per doctype. Everything else on the document is
# either site-side (workbook, folder, preview_image), derived by a controller
# (linked_charts, read back off the resolved items), or identity the sync owns
# (logical_id, is_standard, slug).
# The audience declaration ships with the content — it is the vendor's, and a
# site that wants a different one duplicates.
CARRIED_FIELDS = {
    QUERY: (
        "title",
        "operations",
        "use_live_connection",
        "is_script_query",
        "is_builder_query",
        "is_native_query",
        "sort_order",
        "variables",
    ),
    CHART: (
        "title",
        "query",
        "chart_type",
        "config",
        "sort_order",
        "visibility",
        "visible_to_roles",
        "data_authority",
    ),
    DASHBOARD: (
        "title",
        "items",
        "vertical_compact_layout",
        "visibility",
        "visible_to_roles",
    ),
}

JSON_FIELDS = {"operations", "config", "items"}
CHILD_FIELDS = {"variables", "visible_to_roles"}

# a logical name travels into a logical id, a slug and a file name, so keep it
# to the intersection of what all three accept
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# `{"<chart>": "`<query>`.`<column>`"}` — a filter's link, both sides logical in
# a file and both sides a docname on a site
LINK_COLUMN = re.compile(r"^`([^`]+)`\.`([^`]+)`$")


class BundleError(frappe.ValidationError):
    """A bundle the site cannot honour: malformed files, an unknown format
    version, a duplicate logical name, a reference to an item that is not there.
    Raised per app, and caught per app by `sync_bundles` unless it runs strict."""


@dataclass(frozen=True)
class BundleItem:
    app: str
    bundle: str
    doctype: str
    name: str
    data: dict

    @property
    def logical_id(self) -> str:
        return f"{self.app}/{self.name}"


@dataclass
class Bundle:
    app: str
    folder: str
    path: str
    title: str
    required_apps: list[str]
    format_version: int
    items: list[BundleItem]

    @property
    def key(self) -> str:
        return f"{self.app}/{self.folder}"


@dataclass
class SyncReport:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.created or self.updated or self.deleted)


# ---------------------------------------------------------------- discovery


def discover_bundles(app: str) -> list[Bundle]:
    """The bundles an app ships, read off disk.

    Discovery walks genuinely installed apps and their directories. Reading an
    app's hooks would import it, which is both a cost and a lie on a site where
    the app is only half there — the files are the contract, so look at files.
    """
    root = _bundle_root(app)
    if not root:
        return []

    bundles = []
    for folder in sorted(os.listdir(root)):
        path = os.path.join(root, folder)
        if not os.path.isfile(os.path.join(path, MANIFEST)):
            continue
        bundles.append(_load_bundle(app, folder, path))
    return bundles


def _bundle_root(app: str) -> str | None:
    try:
        root = frappe.get_app_path(app, BUNDLE_DIR)
    except Exception:
        # an installed-but-unimportable app ships nothing we can read
        return None
    return root if os.path.isdir(root) else None


def _load_bundle(app: str, folder: str, path: str) -> Bundle:
    manifest = _read_json(os.path.join(path, MANIFEST))
    if not isinstance(manifest, dict):
        raise BundleError(f"{app}/{folder}: {MANIFEST} must be an object")

    version = cint(manifest.get("format_version") or 1)
    if version > FORMAT_VERSION:
        raise BundleError(
            f"{app}/{folder} is written for bundle format {version}, "
            f"this Insights understands {FORMAT_VERSION}"
        )

    required_apps = manifest.get("required_apps") or []
    if not isinstance(required_apps, list):
        raise BundleError(f"{app}/{folder}: required_apps must be a list")

    items = []
    for type_folder, doctype in ITEM_TYPES.items():
        type_path = os.path.join(path, type_folder)
        if not os.path.isdir(type_path):
            continue
        for file_name in sorted(os.listdir(type_path)):
            if not file_name.endswith(".json"):
                continue
            name = file_name[: -len(".json")]
            if not NAME_PATTERN.match(name):
                raise BundleError(
                    f"{app}/{folder}/{type_folder}/{file_name}: "
                    "a logical name must be lowercase letters, digits, '-' or '_'"
                )
            data = _read_json(os.path.join(type_path, file_name))
            if not isinstance(data, dict):
                raise BundleError(f"{app}/{folder}/{type_folder}/{file_name} must be an object")
            items.append(BundleItem(app=app, bundle=folder, doctype=doctype, name=name, data=data))

    return Bundle(
        app=app,
        folder=folder,
        path=path,
        title=manifest.get("title") or folder,
        required_apps=required_apps,
        format_version=version,
        items=items,
    )


def _read_json(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise BundleError(f"{path} is not valid JSON: {e}") from e
    except OSError as e:
        raise BundleError(f"{path} cannot be read: {e}") from e


# ---------------------------------------------------------------- closure


def dashboard_closure(dashboard: str) -> list[Document]:
    """Everything a dashboard needs, in the order a bundle wants it written.

    The edges are the ones sync remaps on the way in: a dashboard's chart items,
    a chart's source query, and the queries a query reads. What the chart makes
    of those rows is in its config, which travels on the chart itself.

    One definition, because the two things that copy a dashboard are the same
    walk: export writes the closure into an app's bundle, and duplicate writes it
    into a workbook of the caller's own. A second walk would drift the first time
    an edge is added.
    """
    doc = _existing_doc(DASHBOARD, dashboard)

    charts: list[Document] = []
    seen: set[str] = set()
    for entry in frappe.parse_json(doc.items or "[]"):
        chart = entry.get("chart")
        if entry.get("type") == "chart" and chart and chart not in seen:
            seen.add(chart)
            charts.append(_existing_doc(CHART, chart))

    queries: list[Document] = []
    done: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in done:
            return
        if name in visiting:
            raise BundleError(_("Queries reference each other in a cycle, at {0}").format(name))
        visiting.add(name)
        query = _existing_doc(QUERY, name)
        for ref in query_references(frappe.parse_json(query.operations or "[]")):
            visit(str(ref))
        visiting.discard(name)
        done.add(name)
        queries.append(query)

    for chart in charts:
        if chart.query:
            visit(str(chart.query))

    return queries + charts + [doc]


def _existing_doc(doctype: str, name: str) -> Document:
    if not frappe.db.exists(doctype, name):
        raise BundleError(_("{0} {1} is missing, so this dashboard is incomplete").format(doctype, name))
    return frappe.get_doc(doctype, name)


# ------------------------------------------------------------------- sync


def sync_bundles(apps: list[str] | None = None, strict: bool = False) -> SyncReport:
    """Reconcile every installed app's bundles into documents.

    Each app is reconciled inside its own savepoint, so a bundle one app cannot
    ship leaves the others — and the migrate that called this — untouched. That
    failure is logged and recorded on the report; `strict=True` re-raises it
    instead, which is what tests and a developer's own bench want.

    An app, not a bundle, is the unit of isolation, because reconcile is only
    correct on the whole of what an app ships: the flat name namespace is
    checked across an app's bundles, and an item whose file could not be read is
    indistinguishable from one that was removed. Half an app is worse than none.
    """
    report = SyncReport()
    for app in apps or frappe.get_installed_apps():
        savepoint = f"insights_bundles_{app}"
        frappe.db.savepoint(savepoint)
        try:
            sync_app_bundles(app, report)
        except Exception as e:
            frappe.db.rollback(save_point=savepoint)
            report.errors.append(f"{app}: {e}")
            if strict:
                raise
            frappe.log_error(title=f"Failed to sync Insights bundles of {app}", message=str(e))
    return report


def after_app_install(app_name: str) -> SyncReport:
    """An app that arrives brings its analytics with it — the same reconcile as
    migrate, one app wide, and isolated the same way."""
    return sync_bundles([app_name])


def sync_app_bundles(app: str, report: SyncReport | None = None) -> SyncReport:
    """Reconcile one app's bundles."""
    report = report if report is not None else SyncReport()

    with bundle_sync():
        _reconcile_app(app, report)
    return report


def _reconcile_app(app: str, report: SyncReport) -> None:
    bundles = discover_bundles(app)
    existing = _standard_documents(app)
    if not bundles and not existing:
        # the common case by far: an app that ships no analytics
        return

    live_bundles = [b for b in bundles if _has_required_apps(b)]
    desired = _desired_items(app, live_bundles)

    # a logical id must name one document; if an older sync (or a restore) left
    # two, the oldest keeps the id and the rest are cleaned up as stale
    resolved: dict[str, str] = {}
    stale: list[tuple[str, str, str]] = []
    for logical_id, rows in existing.items():
        item = desired.get(logical_id)
        for doctype, name in rows:
            if item and item.doctype == doctype and logical_id not in resolved:
                resolved[logical_id] = name
            else:
                stale.append((doctype, name, logical_id))

    containers = {b.key: _container_workbook(b) for b in live_bundles if b.items}

    # names of items already on the site, so a reference to an item created
    # later in this run still resolves once its turn comes
    name_map = {logical_id.split("/", 1)[1]: name for logical_id, name in resolved.items()}

    for item in _in_dependency_order(desired.values()):
        docname = resolved.get(item.logical_id)
        values = _values_for(item, name_map, containers[f"{item.app}/{item.bundle}"], docname, report)
        name_map[item.name] = _apply(item, docname, values, report)

    _delete_documents(stale, report)
    _cleanup_containers(app, {b.key for b in live_bundles if b.items})


def _has_required_apps(bundle: Bundle) -> bool:
    """A bundle whose required apps are not all installed is not shipped here —
    and if it was shipped before, its documents go, the same as any item whose
    file disappeared. The content is about data that is no longer on the site."""
    return set(bundle.required_apps) <= set(frappe.get_installed_apps())


def _desired_items(app: str, bundles: list[Bundle]) -> dict[str, BundleItem]:
    """Every item the app ships, keyed by logical id. Fails loudly on a
    duplicate name: the namespace is flat per app, so two bundles cannot both
    claim one, and neither can a chart and a query."""
    desired: dict[str, BundleItem] = {}
    for bundle in bundles:
        for item in bundle.items:
            clash = desired.get(item.logical_id)
            if clash:
                raise BundleError(
                    f"{item.logical_id} is shipped twice: "
                    f"{clash.bundle}/{_folder_of(clash.doctype)} and "
                    f"{item.bundle}/{_folder_of(item.doctype)}"
                )
            desired[item.logical_id] = item
    return desired


def _folder_of(doctype: str) -> str:
    return next(folder for folder, dt in ITEM_TYPES.items() if dt == doctype)


def _standard_documents(app: str) -> dict[str, list[tuple[str, str]]]:
    """The app's standard documents, keyed by logical id, oldest first.

    Only `is_standard` documents: a duplicate carries the logical id it was
    copied from, and must never be mistaken for the shipped original.
    """
    found: dict[str, list[tuple[str, str]]] = {}
    for doctype in ITEM_TYPES.values():
        rows = frappe.get_all(
            doctype,
            filters={"is_standard": 1, "logical_id": ("is", "set")},
            fields=["name", "logical_id"],
            order_by="creation asc, name asc",
        )
        for row in rows:
            if row.logical_id.split("/", 1)[0] != app:
                continue
            found.setdefault(row.logical_id, []).append((doctype, row.name))
    return found


def _in_dependency_order(items) -> list[BundleItem]:
    """Queries, then charts, then dashboards — and queries among themselves in
    reference order, so a query that reads another one is written after it. Then
    every reference can be resolved to a docname as it is written, and no item
    needs a second pass."""
    by_type = {folder: [] for folder in ITEM_TYPES}
    for item in items:
        by_type[_folder_of(item.doctype)].append(item)

    ordered = _sort_queries(sorted(by_type["query"], key=lambda i: i.name))
    ordered += sorted(by_type["chart"], key=lambda i: i.name)
    ordered += sorted(by_type["dashboard"], key=lambda i: i.name)
    return ordered


def _sort_queries(queries: list[BundleItem]) -> list[BundleItem]:
    shipped = {item.name: item for item in queries}
    ordered: list[BundleItem] = []
    done: set[str] = set()
    visiting: set[str] = set()

    def visit(item: BundleItem):
        if item.name in done:
            return
        if item.name in visiting:
            raise BundleError(f"queries reference each other in a cycle, at {item.logical_id}")
        visiting.add(item.name)
        for ref in query_references(item.data.get("operations")):
            if ref in shipped:
                visit(shipped[ref])
        visiting.discard(item.name)
        done.add(item.name)
        ordered.append(item)

    for item in queries:
        visit(item)
    return ordered


def query_references(operations) -> list[str]:
    """Every query a query's operations read from. Source, join and union all
    carry `{"type": "query", "query_name": ...}`, at depths this walk does not
    need to know."""
    refs = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("query_name"):
                refs.append(node["query_name"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(operations)
    return refs


# ------------------------------------------------------- writing documents


def _apply(item: BundleItem, docname: str | None, values: dict, report: SyncReport) -> str:
    if docname:
        doc = frappe.get_doc(item.doctype, docname)
        if not _differs(doc, values):
            report.unchanged.append(item.logical_id)
            return docname
        doc.update(values)
        doc.flags.in_bundle_sync = True
        doc.save(ignore_permissions=True)
        report.updated.append(item.logical_id)
        return doc.name

    doc = frappe.new_doc(item.doctype)
    doc.update(values)
    doc.flags.in_bundle_sync = True
    doc.insert(ignore_permissions=True)
    # shipped content belongs to the site, not to whoever ran the migrate
    frappe.db.set_value(item.doctype, doc.name, "owner", "Administrator", update_modified=False)
    report.created.append(item.logical_id)
    return doc.name


def _values_for(
    item: BundleItem,
    name_map: dict[str, str],
    workbook: str,
    docname: str | None,
    report: SyncReport,
) -> dict:
    """The document fields this item wants, references already resolved.

    Identity (`logical_id`, `is_standard`) and the container (`workbook`) are
    part of the wanted values, not set once at creation, so an item that moves
    between bundles moves its document with it.
    """
    data = item.data
    values = {
        "logical_id": item.logical_id,
        "is_standard": 1,
        "workbook": workbook,
    }

    for fieldname in CARRIED_FIELDS[item.doctype]:
        if fieldname not in data:
            continue
        value = data[fieldname]
        if fieldname in CHILD_FIELDS:
            values[fieldname] = _child_rows(fieldname, value)
        elif fieldname in JSON_FIELDS:
            values[fieldname] = frappe.as_json(value) if not isinstance(value, str) else value
        else:
            values[fieldname] = value

    if item.doctype == QUERY and "operations" in values:
        values["operations"] = frappe.as_json(
            _resolve_query_operations(item, frappe.parse_json(values["operations"]), name_map, workbook)
        )

    if item.doctype == CHART and data.get("query"):
        values["query"] = _reference(item, data["query"], name_map)

    if item.doctype == DASHBOARD:
        items = frappe.parse_json(values.get("items") or "[]")
        values["items"] = frappe.as_json(_resolve_dashboard_items(item, items, name_map))
        # the slug is external-facing and assigned once: a site's bookmark
        # outlives any number of syncs
        if not (docname and frappe.db.get_value(DASHBOARD, docname, "slug")):
            values["slug"] = _slug_for(item, docname, report)

    values.setdefault("title", item.name)
    return values


def _child_rows(fieldname: str, value) -> list[dict]:
    rows = []
    for row in value or []:
        # a role table reads better in a file as a plain list of role names
        if fieldname == "visible_to_roles" and isinstance(row, str):
            rows.append({"role": row})
        elif isinstance(row, dict):
            rows.append(dict(row))
        else:
            raise BundleError(f"{fieldname} must be a list of objects, found {type(row).__name__}")
    return rows


def _reference(item: BundleItem, ref: str, name_map: dict[str, str]) -> str:
    name = name_map.get(ref)
    if not name:
        raise BundleError(f"{item.logical_id} references '{ref}', which the app does not ship")
    return name


def _resolve_query_operations(item: BundleItem, operations, name_map: dict[str, str], workbook: str):
    def walk(node):
        if isinstance(node, dict):
            if node.get("query_name"):
                node["query_name"] = _reference(item, node["query_name"], name_map)
                if "workbook" in node:
                    node["workbook"] = workbook
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(operations)
    return operations


def _resolve_dashboard_items(item: BundleItem, items, name_map: dict[str, str]):
    for entry in items:
        if entry.get("type") == "chart" and entry.get("chart"):
            entry["chart"] = _reference(item, entry["chart"], name_map)

        if entry.get("type") == "filter" and entry.get("links"):
            # links are { "<chart>": "`<query>`.`<column>`" }, both sides logical
            links = {}
            for chart, column in entry["links"].items():
                match = LINK_COLUMN.match(column or "")
                if not match:
                    continue
                query, column_name = match.groups()
                links[_reference(item, chart, name_map)] = (
                    f"`{_reference(item, query, name_map)}`.`{column_name}`"
                )
            entry["links"] = links
    return items


def _differs(doc, values: dict) -> bool:
    """Whether writing these values would change the document — the whole of
    sync's idempotency. A run that finds nothing changed saves nothing, so
    `modified` stays where the last real change left it."""
    for fieldname, wanted in values.items():
        current = doc.get(fieldname)
        if fieldname in JSON_FIELDS:
            if frappe.parse_json(current or "null") != frappe.parse_json(wanted or "null"):
                return True
        elif fieldname in CHILD_FIELDS:
            if _stored_rows(doc, fieldname, wanted) != [_scalars(row) for row in wanted]:
                return True
        elif _scalar(current) != _scalar(wanted):
            return True
    return False


def _stored_rows(doc, fieldname: str, wanted: list[dict]) -> list[dict]:
    keys = {key for row in wanted for key in row}
    return [_scalars({key: row.get(key) for key in keys}) for row in doc.get(fieldname) or []]


def _scalars(row: dict) -> dict:
    return {key: _scalar(value) for key, value in row.items()}


def _scalar(value) -> str:
    # link fields to autoincrement doctypes come back as ints, checks as 0/1,
    # everything else as strings — compare them all the same way
    return "" if value is None else str(value)


# ------------------------------------------------------------------ slugs


def _slug_for(item: BundleItem, docname: str | None, report: SyncReport) -> str:
    """A shipped dashboard's external key: its logical name, app-qualified if
    something already holds that slug. Assigned once — the logical name is the
    identity and never changes, so neither does the slug."""
    base = cleanup_page_name(item.name)
    taken = frappe.db.exists(
        DASHBOARD, {"slug": base, "name": ("!=", docname or "")} if docname else {"slug": base}
    )
    if not taken:
        return base

    qualified = cleanup_page_name(f"{item.app}-{item.name}")
    warning = f"slug '{base}' is taken, shipping {item.logical_id} as '{qualified}'"
    report.warnings.append(warning)
    frappe.logger("insights").warning(warning)
    # the dashboard controller adds a numbered suffix if even this is taken
    return append_number_if_name_exists(DASHBOARD, qualified, fieldname="slug")


# -------------------------------------------------------------- deletions


def _delete_documents(rows: list[tuple[str, str, str]], report: SyncReport) -> None:
    """Delete standard documents, dashboards first, so nothing is deleted while
    something still points at it."""
    order = list(ITEM_TYPES.values())[::-1]
    for doctype, name, logical_id in sorted(rows, key=lambda row: order.index(row[0])):
        if frappe.db.exists(doctype, name):
            doc = frappe.get_doc(doctype, name)
            doc.flags.in_bundle_sync = True
            doc.delete(ignore_permissions=True, force=True)
        # a document a controller already took with the one that referenced it
        # is still one this reconcile removed
        report.deleted.append(logical_id)


def before_app_uninstall(app_name: str) -> SyncReport:
    """An app that leaves takes its analytics with it. Duplicates a site made
    are user documents and stay."""
    report = SyncReport()
    with bundle_sync():
        rows = [
            (doctype, name, logical_id)
            for logical_id, found in _standard_documents(app_name).items()
            for doctype, name in found
        ]
        _delete_documents(rows, report)
        _cleanup_containers(app_name, keep=set())
    return report


# -------------------------------------------------- the container workbook


def _container_workbook(bundle: Bundle) -> str:
    """The workbook a bundle's documents live in: one per bundle, owned by
    Administrator, titled from `workbook.json`, created here rather than
    reconciled from the file.

    Which workbook belongs to which bundle is site state, and it is kept where
    the three content doctypes keep theirs: a `logical_id` on the document, the
    bundle key. Sync writes the container and its identity in one transaction,
    so a run that is rolled back leaves neither.
    """
    name = frappe.db.get_value(
        "Insights Workbook", {"logical_id": bundle.key}, "name", order_by="creation asc"
    )
    if name:
        if frappe.db.get_value("Insights Workbook", name, "title") != bundle.title:
            frappe.db.set_value("Insights Workbook", name, "title", bundle.title, update_modified=False)
        return name

    workbook = frappe.new_doc("Insights Workbook")
    workbook.title = bundle.title
    workbook.logical_id = bundle.key
    workbook.insert(ignore_permissions=True)
    frappe.db.set_value("Insights Workbook", workbook.name, "owner", "Administrator", update_modified=False)
    return workbook.name


def standard_content() -> list[dict]:
    """The shipped bundles on this site, as a gallery shows them.

    One entry per container workbook — a bundle is what an app ships and a
    container is what it landed as, so the container is the unit a site sees and
    duplicates. Only dashboards are listed: they are what a bundle is browsed
    by, and the charts and queries under them are reached through them.

    Read through `frappe.get_list` — the permission-checking one — so the
    visibility ladder decides what is in the list. A bundle whose dashboards do
    not admit this user is not in it at all.
    """
    dashboards = frappe.get_list(
        DASHBOARD,
        filters={"is_standard": 1, "logical_id": ("is", "set")},
        fields=["name", "title", "slug", "logical_id", "workbook"],
        order_by="creation asc",
    )

    bundles: dict[str, dict] = {}
    for dashboard in dashboards:
        app = dashboard.logical_id.split("/", 1)[0]
        bundle = bundles.setdefault(
            str(dashboard.workbook),
            {
                "workbook": dashboard.workbook,
                "title": frappe.db.get_value("Insights Workbook", dashboard.workbook, "title"),
                "app": app,
                "app_title": _app_title(app),
                "dashboards": [],
            },
        )
        bundle["dashboards"].append(
            {
                "name": dashboard.name,
                "title": dashboard.title,
                "slug": dashboard.slug,
                "logical_id": dashboard.logical_id,
            }
        )

    return sorted(bundles.values(), key=lambda bundle: (bundle["app_title"], bundle["title"] or ""))


def _app_title(app: str) -> str:
    """The app's display title, for attribution. Falls back to the package name:
    reading the title imports the app, and a broken one should not take the
    whole list down."""
    try:
        return (frappe.get_hooks("app_title", app_name=app) or [app])[0]
    except Exception:
        return app


def _cleanup_containers(app: str, keep: set[str]) -> None:
    """Drop the containers of bundles the app no longer ships. An empty one is
    deleted outright; one a site put its own work into is left alone and merely
    forgotten, so nothing of the site's is destroyed by a bundle going away."""
    for bundle_key, workbook in _containers_of(app).items():
        if bundle_key in keep:
            continue
        if _is_empty(workbook):
            frappe.delete_doc("Insights Workbook", workbook, force=True, ignore_permissions=True)
        else:
            # left with the site's own work in it, and no longer a container
            frappe.db.set_value("Insights Workbook", workbook, "logical_id", None, update_modified=False)


def _containers_of(app: str) -> dict[str, str]:
    rows = frappe.get_all(
        "Insights Workbook",
        filters={"logical_id": ("like", f"{app}/%")},
        fields=["name", "logical_id"],
        order_by="creation asc",
    )
    containers: dict[str, str] = {}
    for row in rows:
        # oldest wins, the same one `_container_workbook` resolves to
        if row.logical_id.split("/", 1)[0] == app:
            containers.setdefault(row.logical_id, row.name)
    return containers


def _is_empty(workbook: str) -> bool:
    return not any(
        frappe.db.exists(doctype, {"workbook": workbook})
        for doctype in (*ITEM_TYPES.values(), "Insights Folder")
    )


# ------------------------------------------------- standard-doc protection


@contextmanager
def bundle_sync():
    """Mark a whole run as the app's own maintenance of the content it ships.

    The per-document `flags.in_bundle_sync` covers what sync writes itself, but a
    controller can cascade into a second standard document, and that one is
    loaded fresh, without flags. So the bypass is request-scoped for the length
    of a run — which is also what it takes to remove shipped documents anywhere
    outside a sync, that being the same work under a different trigger.
    """
    previous = frappe.flags.in_bundle_sync
    frappe.flags.in_bundle_sync = True
    try:
        yield
    finally:
        frappe.flags.in_bundle_sync = previous


def block_standard_edits(doc, method=None):
    """Standard content belongs to the app that ships it: on a site it is
    read-only, and only sync may create it. A developer's bench is the exception
    — that is where shipped content is authored and iterated on."""
    if not _is_standard(doc) or _sync_or_developer(doc):
        return

    if doc.is_new():
        frappe.throw(_("Standard content can only be created by the app that ships it."))

    frappe.throw(_("Standard content is read-only. Duplicate it to make changes."))


def block_standard_deletes(doc, method=None):
    if not _is_standard(doc) or _sync_or_developer(doc):
        return

    frappe.throw(_("Standard content is read-only. It is removed when its app is uninstalled."))


def _is_standard(doc) -> bool:
    """True for a document that is standard now or was before this save — so
    clearing the flag is itself an edit of standard content, not a way around
    the check."""
    if doc.get("is_standard"):
        return True
    if doc.is_new():
        return False
    before = doc.get_doc_before_save()
    if before is not None:
        return bool(before.get("is_standard"))
    return bool(frappe.db.get_value(doc.doctype, doc.name, "is_standard"))


def _sync_or_developer(doc) -> bool:
    return bool(doc.flags.in_bundle_sync or frappe.flags.in_bundle_sync or frappe.conf.developer_mode)
