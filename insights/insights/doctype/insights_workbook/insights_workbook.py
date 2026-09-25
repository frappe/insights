# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.model.naming import getseries
from frappe.model.rename_doc import rename_doc
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
from frappe.website.utils import cleanup_page_name

from insights import standard
from insights.desk import claims_on, refuse_delete_while_claimed
from insights.insights.query_utils import referenced_queries
from insights.permissions import ROLES, can_copy, can_write, check_trusted_code_author
from insights.telemetry import capture
from insights.utils import deep_convert_dict_to_dict

# `tabSeries` key the workbook counter lives under.
WORKBOOK_SERIES_KEY = "Insights Workbook"

# Where an open came from, as `docs/telemetry.md` names them.
OPEN_VIA = {"list", "recent", "desk", "link"}

# The file key for each member doctype. The file does not name the doctype, so
# renaming a doctype changes no file an app ships.
MEMBER_DOCTYPES = {
    "queries": "Insights Query v3",
    "charts": "Insights Chart v3",
    "dashboards": "Insights Dashboard v3",
}


def standard_dashboard_visibility() -> dict:
    """The visibility of a dashboard an app ships.

    Frappe gives Desk User to every System User automatically. So the list
    needs no upkeep, and portal users do not see desk content.
    """
    return {"visibility": ROLES, "visible_to_roles": [{"role": "Desk User"}]}


class InsightsWorkbook(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        data_backup: DF.JSON | None
        is_standard: DF.Check
        module: DF.Link | None
        title: DF.Data
    # end: auto-generated types

    @staticmethod
    def prepare_for_import(docdict: dict) -> None:
        standard.validate_overwrite(docdict)

    def before_naming(self):
        # a fixture or export written while this doctype was still `autoincrement` has a
        # numeric name, and the column is varchar now — `validate_name` throws on an int
        if isinstance(self.name, int):
            self.name = str(self.name)

    def autoname(self):
        # plain numbers, continuing from where `autoincrement` left off — see
        # insights/patches/name_workbooks_as_strings.py for why this needs to be a string.
        self.name = getseries(WORKBOOK_SERIES_KEY, 1)

    def validate(self):
        standard.validate_standard(self)

        if self.is_standard and not self.module:
            frappe.throw(frappe._("A standard workbook must name the module it ships in."))

        # `module` links to `Module Def`, which also holds a site's own modules.
        # The framework reads shipped files only from installed apps'
        # `modules.txt`. The check is here, not in `mark_as_standard`, so a plain
        # save, a bench console and the workbook CLI all get it.
        if self.is_standard and not standard.ships_module(self.module):
            frappe.throw(
                frappe._(
                    "No installed app ships the module {0}, so the next migrate would delete this workbook and everything in it."
                ).format(frappe.bold(self.module))
            )

        if not self.is_standard:
            self.module = None

    def before_save(self):
        self.title = self.title or f"Workbook {self.name}"

    def on_update(self):
        standard.export(self)

    def before_rename(self, old_name, new_name, merge=False):
        standard.validate_standard(self)

        if self.is_standard:
            # Every rename of a standard workbook must check its file is free, not only
            # `mark_as_standard`. Two names can scrub to one filename. Then
            # `after_rename` overwrites the other workbook's file, and the next
            # migrate deletes that workbook as an orphan.
            standard.check_file_is_free(self.doctype, new_name, self.module)

    def after_rename(self, old_name, new_name, merge=False):
        standard.delete_folder(self, old_name)
        standard.export(self)

    def on_trash(self):
        standard.validate_standard(self)
        if not self.flags.force_delete:
            self.check_if_members_are_claimed()

        try:
            backup_data = frappe.as_json(self.export())
            self.db_set("data_backup", backup_data)
        except Exception as e:
            frappe.log_error(f"Failed to backup workbook {self.name}: {e!s}")

        with standard.deleting(self.name):
            # Delete dashboards first. Then a chart's delete finds no dashboard
            # in this workbook to remove its cells from.
            for d in frappe.get_all("Insights Dashboard v3", {"workbook": self.name}):
                frappe.delete_doc("Insights Dashboard v3", d.name, force=True, ignore_permissions=True)
            for q in frappe.get_all("Insights Query v3", {"workbook": self.name}):
                frappe.delete_doc("Insights Query v3", q.name, force=True, ignore_permissions=True)
            for c in frappe.get_all("Insights Chart v3", {"workbook": self.name}):
                frappe.delete_doc("Insights Chart v3", c.name, force=True, ignore_permissions=True)
            for f in frappe.get_all("Insights Folder", {"workbook": self.name}):
                frappe.delete_doc("Insights Folder", f.name, force=True, ignore_permissions=True)

        standard.delete_folder(self)

    def check_if_members_are_claimed(self):
        """Refuse the delete while a desk document shows one of its members.

        The members are deleted with `force=True`, which skips the link check
        that would refuse each delete. So the check runs here instead. A forced
        workbook delete skips it too, like frappe's own link check, so a re-sync
        is never blocked.
        """
        refuse_delete_while_claimed(
            self.title or self.name,
            [
                claim
                for doctype in MEMBER_DOCTYPES.values()
                for claim in claims_on(doctype, {"workbook": self.name})
            ],
        )

    def after_insert(self):
        if frappe.flags.in_import:
            self.restore_imported_members()
            return

        capture("workbook_created")

        # If this is a restored workbook (has data_backup) then restore child documents
        if not self.data_backup:
            # This is a normal new workbook and not a restored one(skip restore)
            return

        self.restore_workbook_contents(self.data_backup, self.name, ignore_permissions=True)
        self.db_set("data_backup", None)

    def restore_imported_members(self):
        """Restore the members in the file, under the names the file gives them.

        This is the counterpart of `before_export`. `import_doc` builds the
        workbook from the whole file, so the members arrive as attributes on the
        document, not as fields. A standard workbook is the same document on
        every site, so no name changes.
        """
        file = {key: self.get(key) for key in ("folders", *MEMBER_DOCTYPES) if self.get(key) is not None}
        self.restore_workbook_contents(file, self.name, ignore_permissions=True, keep_names=True)

    def restore_workbook_contents(
        self,
        workbook_data,
        target_workbook_name,
        ignore_permissions=False,
        keep_names=False,
    ):
        """Restore the workbook's contents, and answer with the name each one took.

        The map is keyed on the name the file includes and valued on the name the
        copy got, so a caller can reach what it just imported.

        With `keep_names`, the file is restored as written. Each member keeps the
        name the file gives it. A member the site already has is updated in
        place. Members the file no longer includes are deleted. A standard
        workbook arrives this way. Every other restore gives members new names
        and rewrites the references to them.
        """
        contents = workbook_contents(workbook_data)
        queries = contents["queries"]
        charts = contents["charts"]
        dashboards = contents["dashboards"]

        check_trusted_code_author(
            [
                (
                    query.get("title") or name,
                    query.get("operations"),
                    frappe.db.get_value("Insights Query v3", name, "operations") if keep_names else None,
                )
                for name, query in queries.items()
            ]
            + [
                (
                    chart.get("title") or name,
                    chart.get("config"),
                    frappe.db.get_value("Insights Chart v3", name, "config") if keep_names else None,
                )
                for name, chart in charts.items()
            ]
        )

        id_map = {}
        if contents.get("name"):
            id_map[contents["name"]] = target_workbook_name
        if keep_names:
            id_map.update({name: name for name in (*queries, *charts, *dashboards)})

        # Not in `id_map`: a folder is keyed by title and a member by docname. In
        # one dict, a folder titled like a query would replace that query's entry.
        folders = _restore_folders(
            contents["folders"],
            target_workbook_name,
            keep_names=keep_names,
            ignore_permissions=ignore_permissions,
        )

        query_sort_order = 0
        for name in _order_by_reference(queries):
            query = deep_convert_dict_to_dict(queries[name])
            query["operations"] = _rewrite_query_references(
                query.get("operations"), id_map, target_workbook_name
            )
            query["folder"] = folders.get(("query", query.get("folder")))
            if query.get("sort_order") is None:
                query["sort_order"] = query_sort_order
                query_sort_order += 1

            id_map[name] = _restore_member(
                "Insights Query v3", name, query, target_workbook_name, keep_names, ignore_permissions
            )

        chart_sort_order = 0
        for name, chart in charts.items():
            chart = deep_convert_dict_to_dict(chart)
            chart["query"] = id_map.get(chart.get("query"), chart.get("query"))
            chart["folder"] = folders.get(("chart", chart.get("folder")))
            if chart.get("sort_order") is None:
                chart["sort_order"] = chart_sort_order
                chart_sort_order += 1
            if keep_names:
                # The file never sets this. So a hand-edited file cannot make a
                # standard chart run as owner.
                chart["run_as_owner"] = 0

            id_map[name] = _restore_member(
                "Insights Chart v3", name, chart, target_workbook_name, keep_names, ignore_permissions
            )

        for name, dashboard in dashboards.items():
            dashboard = deep_convert_dict_to_dict(dashboard)
            dashboard["items"] = frappe.as_json(_rewrite_dashboard_items(dashboard.get("items"), id_map))
            if keep_names:
                # The file never sets these. So a hand-edited file cannot hide a
                # shipped dashboard from desk users.
                dashboard.update(standard_dashboard_visibility())

            id_map[name] = _restore_member(
                "Insights Dashboard v3",
                name,
                dashboard,
                target_workbook_name,
                keep_names,
                ignore_permissions,
            )

        if keep_names:
            _delete_dropped_members(target_workbook_name, contents)

        return id_map

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)

        d.folders = frappe.get_all(
            "Insights Folder",
            filters={"workbook": self.name},
            fields=[
                "name",
                "title",
                "type",
                "sort_order",
            ],
            order_by="sort_order asc, creation asc",
        )

        d.queries = frappe.get_all(
            "Insights Query v3",
            filters={"workbook": self.name},
            fields=[
                "name",
                "title",
                "folder",
                "sort_order",
                "is_native_query",
                "is_builder_query",
                "is_script_query",
            ],
            order_by="sort_order asc, creation asc",
        )
        d.charts = frappe.get_all(
            "Insights Chart v3",
            filters={"workbook": self.name},
            fields=[
                "name",
                "title",
                "folder",
                "sort_order",
                "chart_type",
                "query",
            ],
            order_by="sort_order asc, creation asc",
        )
        d.dashboards = frappe.get_all(
            "Insights Dashboard v3",
            filters={"workbook": self.name},
            fields=["name", "title"],
            order_by="creation asc",
        )
        d.folders = frappe.as_json(d.folders)
        d.queries = frappe.as_json(d.queries)
        d.charts = frappe.as_json(d.charts)
        d.dashboards = frappe.as_json(d.dashboards)
        d.read_only = not can_write(self)
        d.can_copy = can_copy(self)
        return d

    @frappe.whitelist()
    def track_view(self, via: str | None = None):
        view_log = frappe.qb.DocType("View Log")
        last_viewed_recently = frappe.db.get_value(
            view_log,
            filters=(
                (view_log.creation > (Now() - Interval(minutes=5)))
                & (view_log.reference_doctype == self.doctype)
                & (view_log.reference_name == self.name)
                & (view_log.viewed_by == frappe.session.user)
            ),
            pluck="name",
        )
        if not last_viewed_recently:
            self.add_viewed(force=True)

        capture("workbook_opened", interval="1d", via=via if via in OPEN_VIA else "link")

    @frappe.whitelist()
    def export(self):
        """The workbook and its members, in file format.

        The download, Duplicate, the backup a delete keeps, and the file an app
        ships all use this format.
        """
        return {
            "doctype": self.doctype,
            "name": self.name,
            "title": self.title,
            **self.export_members(),
        }

    def before_export(self, doc_export: dict) -> None:
        """Add the members to the file frappe is about to write.

        `as_dict` adds a summary of each member list for the frontend sidebar.
        The file needs the full members instead. A member kept for desk no
        longer belongs to the app, so it is left out.
        """
        doc_export.update(self.export_members(shipped=True))
        for field in ("read_only", "can_copy", "data_backup"):
            doc_export.pop(field, None)

    def export_members(self, shipped: bool = False) -> dict:
        """The workbook's queries, charts, dashboards and folders. With `shipped`,
        only the members its app ships.

        A member refers to its folder by title. The folder's name is a hash, and
        the importing site makes its own.
        """
        filters = {"workbook": self.name}
        if shipped:
            filters["kept_for_desk"] = 0

        queries = frappe.get_all(
            "Insights Query v3",
            filters=filters,
            fields=[
                "name",
                "title",
                "workbook",
                "folder",
                "sort_order",
                "use_live_connection",
                "is_script_query",
                "is_builder_query",
                "is_native_query",
                "operations",
            ],
            order_by="creation asc",
        )
        charts = frappe.get_all(
            "Insights Chart v3",
            filters=filters,
            fields=[
                "name",
                "title",
                "workbook",
                "folder",
                "sort_order",
                "query",
                "chart_type",
                "config",
            ],
            order_by="creation asc",
        )
        dashboards = frappe.get_all(
            "Insights Dashboard v3",
            filters=filters,
            fields=[
                "name",
                "title",
                "workbook",
                "items",
                "vertical_compact_layout",
            ],
            order_by="creation asc",
        )

        active_folders = {member.folder for member in (*queries, *charts) if member.folder}
        folders = (
            frappe.get_all(
                "Insights Folder",
                filters={"workbook": self.name, "name": ["in", list(active_folders)]},
                fields=["name", "title", "type", "sort_order"],
                order_by="sort_order asc, creation asc",
            )
            if active_folders
            else []
        )
        folder_title = {folder.name: folder.title for folder in folders}

        for q in queries:
            q.operations = frappe.parse_json(q.operations)
            q.folder = folder_title.get(q.folder)
        for c in charts:
            c.config = frappe.parse_json(c.config)
            c.folder = folder_title.get(c.folder)
        for d in dashboards:
            d["items"] = frappe.parse_json(d["items"])

        return {
            "folders": [{"title": f.title, "type": f.type, "sort_order": f.sort_order} for f in folders],
            "queries": {q.name: q for q in queries},
            "charts": {c.name: c for c in charts},
            "dashboards": {d.name: d for d in dashboards},
        }

    @frappe.whitelist()
    def mark_as_standard(self, name: str | None = None, module: str | None = None):
        """Make this workbook standard in `module`, and return its new name.

        The names identify the workbook on every site that installs the file.
        So they are readable, and they are set once, here. The workbook takes
        `name`. Each member takes `<workbook>-<title slug>`. Every reference in
        `operations`, `items` and a filter's `links` is rewritten to match.
        """
        if not frappe.conf.developer_mode:
            frappe.throw(frappe._("A workbook is marked standard in developer mode."))

        frappe.only_for("Insights Admin")
        self.check_permission("write")

        if not module:
            frappe.throw(frappe._("Name the module the workbook ships in."))

        name = cleanup_page_name(name or self.title)
        if not name:
            frappe.throw(frappe._("Name the workbook ships under."))

        standard.check_file_is_free(self.doctype, name, module)

        if name != self.name:
            rename_doc(self.doctype, self.name, name, force=True, ignore_permissions=True)
        renames = _rename_members(name)

        for doctype, old, new in renames:
            rename_doc(doctype, old, new, force=True, ignore_permissions=True)

        id_map = {old: new for _, old, new in renames}
        _rewrite_member_references(name, id_map)

        # Save the workbook first. Each member reads its `is_standard` from it.
        workbook = frappe.get_doc(self.doctype, name)
        workbook.is_standard = 1
        workbook.module = module
        workbook.save()

        # Then the dashboards. A chart on a Public dashboard must run as owner,
        # and a shipped chart must not. So no dashboard stays Public.
        for dashboard in frappe.get_all("Insights Dashboard v3", {"workbook": name}, pluck="name"):
            doc = frappe.get_doc("Insights Dashboard v3", dashboard)
            doc.update(standard_dashboard_visibility())
            doc.save(ignore_permissions=True)
        # Save each chart as a document, so `validate_run_as_owner` runs. It
        # makes sure a shipped chart does not run as owner.
        for chart in frappe.get_all("Insights Chart v3", {"workbook": name}, pluck="name"):
            doc = frappe.get_doc("Insights Chart v3", chart)
            doc.run_as_owner = 0
            doc.save(ignore_permissions=True)

        return name

    @frappe.whitelist()
    def duplicate(self):
        workbook = self.export()
        workbook["title"] = None
        return import_workbook(workbook)["workbook"]

    @frappe.whitelist()
    def import_query(self, query: dict | str):
        from insights.insights.doctype.insights_query_v3.insights_query_v3 import import_query

        return import_query(query, self.name)

    @frappe.whitelist()
    def import_chart(self, chart: dict | str):
        from insights.insights.doctype.insights_chart_v3.insights_chart_v3 import import_chart

        return import_chart(chart, self.name)

    @frappe.whitelist()
    def get_lineage_graph(self):
        """Return query-reference graph nodes and edges for queries in this workbook,
        including all upstream table and query dependencies."""
        frappe.only_for("Insights Admin")

        Ref = frappe.qb.DocType("Insights Query Reference")
        Query = frappe.qb.DocType("Insights Query v3")

        edges = (
            frappe.qb.from_(Ref)
            .join(Query)
            .on(Query.name == Ref.query)
            .select(
                Ref.ref_type,
                Ref.query,
                Query.title.as_("query_title"),
                Query.workbook,
                Ref.data_source,
                Ref.table_name,
                Ref.ref_query,
            )
            .where(Query.workbook == self.name)
            .run(as_dict=True)
        )

        dep_query_names = list({e.ref_query for e in edges if e.ref_type == "Query" and e.ref_query})
        dep_titles: dict[str, dict] = {}
        if dep_query_names:
            for row in frappe.get_all(
                "Insights Query v3",
                filters={"name": ("in", dep_query_names)},
                fields=["name", "title", "workbook"],
            ):
                dep_titles[row.name] = row

        nodes: dict[str, dict] = {}
        edge_list: list[dict] = []

        for e in edges:
            q_id = f"query::{e.query}"
            nodes[q_id] = {
                "id": q_id,
                "node_type": "query",
                "label": e.query_title or e.query,
                "name": e.query,
                "workbook": e.workbook,
            }

            if e.ref_type == "Table":
                t_id = f"table::{e.data_source}::{e.table_name}"
                nodes.setdefault(
                    t_id,
                    {
                        "id": t_id,
                        "node_type": "table",
                        "label": e.table_name,
                        "data_source": e.data_source,
                    },
                )
                edge_list.append({"id": f"{t_id}=>{q_id}", "source": t_id, "target": q_id})

            elif e.ref_type == "Query" and e.ref_query:
                dep_id = f"query::{e.ref_query}"
                if dep_id not in nodes:
                    info = dep_titles.get(e.ref_query, {})
                    nodes[dep_id] = {
                        "id": dep_id,
                        "node_type": "query",
                        "label": info.get("title") or e.ref_query,
                        "name": e.ref_query,
                        "workbook": info.get("workbook"),
                    }
                edge_list.append({"id": f"{dep_id}=>{q_id}", "source": dep_id, "target": q_id})

        return {
            "nodes": list(nodes.values()),
            "edges": edge_list,
        }


def _order_by_reference(queries: dict) -> list[str]:
    """The names in `queries`, each one after the queries in the file it references.

    A query is inserted with its references already pointing at the copies they
    name, so those copies have to exist first. References form a directed acyclic
    graph, so such an order exists. A file with no such order has a cycle.
    """
    deps = {
        name: referenced_queries(query.get("operations")) & queries.keys() for name, query in queries.items()
    }

    ordered = []
    placed = set()
    while len(placed) < len(deps):
        ready = [name for name, refs in deps.items() if name not in placed and refs <= placed]
        if not ready:
            frappe.throw(
                frappe._("Circular query reference detected in {0}").format(
                    ", ".join(name for name in deps if name not in placed)
                )
            )
        ordered.extend(ready)
        placed.update(ready)

    return ordered


def _rename_members(workbook: str) -> list[tuple[str, str, str]]:
    """The new name of each member, as `<workbook>-<title slug>`.

    Two members can have the same title, and another document can already use
    the name. So a taken name gets a number.
    """
    renames = []
    taken = set()
    for doctype in MEMBER_DOCTYPES.values():
        members = frappe.get_all(
            doctype, filters={"workbook": workbook}, fields=["name", "title"], order_by="creation asc"
        )
        for member in members:
            slug = cleanup_page_name(member.title) or "item"
            new_name = f"{workbook}-{slug}"
            suffix = 1
            while new_name in taken or _answered_by_another(doctype, member.name, new_name):
                suffix += 1
                new_name = f"{workbook}-{slug}-{suffix}"

            taken.add(new_name)
            if new_name != member.name:
                renames.append((doctype, member.name, new_name))

    return renames


def _answered_by_another(doctype: str, member: str, name: str) -> bool:
    """Whether a document other than `member` already uses `name`.

    A dashboard opens by its route as well as by its docname.
    `resolver.resolve` tries the docname first, so routes and docnames share
    one keyspace. If a member takes a docname equal to a site dashboard's
    route, every link to that route opens the member instead. Saving again
    does not fix it, because `set_route` only resets the shipped dashboard's
    own route.

    This calls `InsightsDashboardv3.answered_by_another` instead of repeating
    its two lookups, because renaming here also writes into that keyspace.
    """
    if doctype == MEMBER_DOCTYPES["dashboards"]:
        return frappe.get_doc(doctype, member).answered_by_another(name)

    return name != member and bool(frappe.db.exists(doctype, name))


def _rewrite_member_references(workbook: str, id_map: dict) -> None:
    """Update every reference inside a member's JSON to the member's new name.

    `rename_doc` updates Link fields only. A name inside `operations` or a
    dashboard's `items` is not a Link field.

    A reference also names the workbook, which may have been renamed. So a
    member that kept its name still goes in the map, mapped to itself.
    """
    id_map = dict(id_map)
    for doctype in MEMBER_DOCTYPES.values():
        for member in frappe.get_all(doctype, filters={"workbook": workbook}, pluck="name"):
            id_map.setdefault(member, member)

    for query in frappe.get_all(
        "Insights Query v3", filters={"workbook": workbook}, fields=["name", "operations"]
    ):
        frappe.db.set_value(
            "Insights Query v3",
            query.name,
            "operations",
            _rewrite_query_references(query["operations"], id_map, workbook),
            update_modified=False,
        )

    for dashboard in frappe.get_all(
        "Insights Dashboard v3", filters={"workbook": workbook}, fields=["name", "items"]
    ):
        frappe.db.set_value(
            "Insights Dashboard v3",
            dashboard.name,
            "items",
            frappe.as_json(_rewrite_dashboard_items(dashboard["items"], id_map)),
            update_modified=False,
        )


def is_workbook_file(workbook_data) -> bool:
    """Whether `workbook_contents` can read this file.

    A file has the `doctype` it was exported from. A file in the old wrapped
    format has `type` set to `Workbook` instead.
    """
    try:
        data = frappe.parse_json(workbook_data)
    except ValueError:
        return False
    return isinstance(data, dict) and (
        data.get("doctype") == "Insights Workbook" or data.get("type") == "Workbook"
    )


def workbook_contents(workbook_data) -> "frappe._dict":
    """A workbook file, with its members at the top level.

    The old format put the workbook in `doc` and its members in
    `dependencies`. This function flattens that format, so one reader works for
    the files an app ships and for every file a site exported before.
    """
    data = deep_convert_dict_to_dict(frappe.parse_json(workbook_data) or {})
    if "doc" in data or "dependencies" in data:
        lifted = deep_convert_dict_to_dict(data.get("doc") or {})
        lifted.update(data.get("dependencies") or {})
        lifted.setdefault("name", data.get("name"))
        data = lifted

    data.setdefault("folders", [])
    for key in MEMBER_DOCTYPES:
        data.setdefault(key, {})

    return data


def _restore_folders(folders, workbook: str, keep_names: bool, ignore_permissions: bool) -> dict:
    """Create or update a folder on this site for every folder in the file.

    Returns a map from the file's folder key to the site's folder name. A file
    refers to a folder by title. An older file refers to it by the hash the
    exporting site made. So the map has both keys.

    The key includes the folder `type`, because a folder is unique by type and
    title. A query folder and a chart folder can have the same title.
    """
    on_site = {}
    if keep_names:
        on_site = {
            (row.type, row.title): row.name
            for row in frappe.get_all(
                "Insights Folder", filters={"workbook": workbook}, fields=["name", "title", "type"]
            )
        }

    folder_map = {}
    for folder in folders:
        folder = deep_convert_dict_to_dict(folder)
        existing = on_site.get((folder["type"], folder["title"]))
        doc = frappe.get_doc("Insights Folder", existing) if existing else frappe.new_doc("Insights Folder")
        doc.title = folder["title"]
        doc.type = folder["type"]
        doc.sort_order = folder.get("sort_order") or 0
        doc.workbook = workbook
        if existing:
            doc.save(ignore_permissions=ignore_permissions)
        else:
            doc.insert(ignore_permissions=ignore_permissions)

        folder_map[(folder["type"], folder["title"])] = doc.name
        if folder.get("name"):
            folder_map[(folder["type"], folder["name"])] = doc.name

    return folder_map


def _restore_member(
    doctype: str, name: str, payload: dict, workbook: str, keep_names: bool, ignore_permissions: bool
) -> str:
    """Restore one member and return its name."""
    existing = keep_names and frappe.db.exists(doctype, name)
    if keep_names:
        _refuse_a_borrowed_row(doctype, name, workbook)

    doc = frappe.get_doc(doctype, name) if existing else frappe.new_doc(doctype)
    doc.update(payload)
    doc.workbook = workbook

    if existing:
        doc.save(ignore_permissions=ignore_permissions)
    elif keep_names:
        doc.insert(ignore_permissions=ignore_permissions, set_name=name)
    else:
        doc.insert(ignore_permissions=ignore_permissions)

    return doc.name


def _refuse_a_borrowed_row(doctype: str, name: str, workbook: str) -> None:
    """Refuse to import a member whose name belongs to another workbook.

    With `keep_names`, the name comes from the file. A member is named
    `<workbook>-<title slug>`, and the name is made unique only on the bench
    that wrote the file. A site that installs two apps can therefore get a
    name collision that neither app's bench could see. Reusing the row would
    move the other app's chart into this workbook. The other app's dashboard
    would then show that chart, and nothing on screen would say so.

    A dashboard also opens by its route. So a name that no row has can still
    be a site dashboard's route. `resolver.resolve` tries the docname first, so
    a member inserted under that name takes over every link to the route.
    `_rename_members` checks this on the bench that makes the name. Only the
    installing site can see a collision between two apps, so it checks too.

    Frappe's `validate_overwrite` gives this refusal for the workbook itself.
    Insights restores the members, so it gives the same refusal for them.
    """
    holder = frappe.db.get_value(doctype, name, "workbook")
    if holder:
        if holder == workbook:
            return

        frappe.throw(
            frappe._("{0} {1} already belongs to the workbook {2}.").format(
                doctype, frappe.bold(name), frappe.bold(holder)
            )
        )

    answering = _answers_to_route(doctype, name)
    if answering:
        frappe.throw(
            frappe._("The dashboard {0} already answers to {1}.").format(
                frappe.bold(answering), frappe.bold(name)
            )
        )


def _answers_to_route(doctype: str, name: str) -> str | None:
    """The dashboard whose route is `name`, if one exists."""
    if doctype != MEMBER_DOCTYPES["dashboards"]:
        return None

    return frappe.db.get_value(doctype, {"route": name, "name": ("!=", name)}, "name")


def _delete_dropped_members(workbook: str, contents: dict) -> None:
    """Delete the members of `workbook` the file no longer includes.

    A member that a desk document shows is kept, with the charts and queries
    it reads, and the keep is logged. Deleting it would leave the desk
    document linked to nothing. Refusing would block the migrate. A kept member
    is marked `kept_for_desk`, so the next export leaves it out. Dashboards are
    deleted first, so a chart is off every dashboard before it goes. Folders
    are deleted last, so no member is still in one.
    """
    dropped = {
        key: [
            name
            for name in frappe.get_all(MEMBER_DOCTYPES[key], filters={"workbook": workbook}, pluck="name")
            if name not in contents[key]
        ]
        for key in ("dashboards", "charts", "queries")
    }
    kept = _kept_for_desk(workbook, dropped)

    for key in ("dashboards", "charts", "queries"):
        for name in dropped[key]:
            if name not in kept:
                frappe.delete_doc(MEMBER_DOCTYPES[key], name, force=True, ignore_permissions=True)

    for doctype in MEMBER_DOCTYPES.values():
        for name, was_kept in frappe.get_all(
            doctype, filters={"workbook": workbook}, fields=["name", "kept_for_desk"], as_list=True
        ):
            if bool(was_kept) != (name in kept):
                frappe.db.set_value(doctype, name, "kept_for_desk", int(name in kept), update_modified=False)

    kept_folders = {
        folder
        for key in ("charts", "queries")
        for folder in frappe.get_all(
            MEMBER_DOCTYPES[key], filters={"name": ("in", sorted(kept))}, pluck="folder"
        )
        if folder
    }
    in_file = {(folder["type"], folder["title"]) for folder in contents["folders"]}
    for folder in frappe.get_all(
        "Insights Folder", filters={"workbook": workbook}, fields=["name", "title", "type"]
    ):
        if (folder.type, folder.title) not in in_file and folder.name not in kept_folders:
            frappe.delete_doc("Insights Folder", folder.name, force=True, ignore_permissions=True)


def _kept_for_desk(workbook: str, dropped: dict) -> set[str]:
    """The dropped members to keep for desk.

    These are the members a desk document shows, the charts on a kept
    dashboard, and the queries those charts read.
    """
    from insights.insights.query_utils import transitive_closure

    claims = [
        claim
        for key in ("dashboards", "charts")
        if dropped[key]
        for claim in claims_on(MEMBER_DOCTYPES[key], {"name": ("in", dropped[key])})
    ]
    if not claims:
        return set()

    kept = {claimed for _, _, claimed in claims}
    for items in frappe.get_all(
        MEMBER_DOCTYPES["dashboards"], filters={"name": ("in", sorted(kept))}, pluck="items"
    ):
        kept |= {
            item.get("chart") for item in frappe.parse_json(items) or [] if item.get("type") == "chart"
        } & set(dropped["charts"])

    for query in frappe.get_all(
        MEMBER_DOCTYPES["charts"], filters={"name": ("in", sorted(kept))}, pluck="query"
    ):
        if query:
            kept |= {query, *transitive_closure(query)} & set(dropped["queries"])

    # Every migrate checks the kept members again, so log only new ones.
    already_kept = {
        name
        for doctype in MEMBER_DOCTYPES.values()
        for name in frappe.get_all(doctype, filters={"workbook": workbook, "kept_for_desk": 1}, pluck="name")
    }
    newly_claimed = [claim for claim in claims if claim[2] not in already_kept]
    if newly_claimed:
        frappe.log_error(
            title=f"Kept what a desk document uses in {workbook}",
            message="\n".join(
                f"{desk_doctype} {desk_name} uses {claimed}, which the file no longer includes"
                for desk_doctype, desk_name, claimed in newly_claimed
            ),
        )
    return kept


def delete_unclaimed_kept_members() -> None:
    """Delete a member kept for desk once no desk document shows it.

    Frappe imports a file again only when the file changes. Without this, a
    kept member would stay, read-only, until the app changed that file.
    """
    from frappe.modules.import_file import read_doc_from_file

    kept_in = {
        workbook
        for doctype in MEMBER_DOCTYPES.values()
        for workbook in frappe.get_all(doctype, filters={"kept_for_desk": 1}, pluck="workbook")
    }
    if not kept_in:
        return

    for workbook in frappe.get_all(
        "Insights Workbook",
        filters={"name": ("in", sorted(kept_in)), "is_standard": 1},
        fields=["name", "module"],
    ):
        path = standard.file_path("Insights Workbook", workbook.name, workbook.module)
        _delete_dropped_members(workbook.name, workbook_contents(read_doc_from_file(path)))


def _rewrite_dashboard_items(items, id_map: dict) -> list:
    """Update every chart and filter link in `items` to the new chart name."""
    items = deep_convert_dict_to_dict(frappe.parse_json(items) or [])
    for item in items:
        if item.get("type") == "chart" and item.get("chart") in id_map:
            item["chart"] = id_map[item["chart"]]

        if item.get("type") == "filter" and item.get("links"):
            new_links = {}
            for chart_name, field in item["links"].items():
                if chart_name not in id_map or not field or "`.`" not in field:
                    continue

                field_query = field.split("`.`")[0].replace("`", "")
                field_name = field.split("`.`")[1].replace("`", "")

                if field_query not in id_map:
                    continue

                new_links[id_map[chart_name]] = f"`{id_map[field_query]}`.`{field_name}`"

            item["links"] = new_links

    return items


def _rewrite_query_references(operations, id_map: dict, workbook: str | None = None) -> str:
    """Point every reference in `operations` at the copy that replaces it.

    A reference names a query and the workbook of that query, so both change
    together. `workbook` is the workbook of the copies.

    A name that is not in the map is a query already on this site. It stays
    as it is: the import refers to that query, and read access decides whether
    it runs.
    """
    operations = deep_convert_dict_to_dict(frappe.parse_json(operations) or [])
    for op in operations:
        table = op.get("table") or {}
        if table.get("type") != "query" or table.get("query_name") not in id_map:
            continue

        table["query_name"] = id_map[table["query_name"]]
        if workbook:
            table["workbook"] = workbook

    return frappe.as_json(operations)


def import_workbook(workbook):
    if not is_workbook_file(workbook):
        frappe.throw(frappe._("This is not a workbook file"))
    workbook = workbook_contents(workbook)

    # Create a new Insights Workbook
    new_workbook = frappe.new_doc("Insights Workbook")
    new_workbook.title = workbook.get("title")
    new_workbook.insert()
    id_map = new_workbook.restore_workbook_contents(
        workbook,
        new_workbook.name,
    )

    return {"workbook": new_workbook.name, "names": id_map}
