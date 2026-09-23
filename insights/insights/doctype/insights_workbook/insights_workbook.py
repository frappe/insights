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
from insights.permissions import ROLES, can_write, check_trusted_code_author
from insights.telemetry import capture
from insights.utils import deep_convert_dict_to_dict

# `tabSeries` key the workbook counter lives under.
WORKBOOK_SERIES_KEY = "Insights Workbook"

# Where an open came from, as `docs/telemetry.md` names them.
OPEN_VIA = {"list", "recent", "desk", "link"}

# The key a workbook file carries each kind of member under. The file names no
# member doctype, so renaming one touches no file an app ships.
MEMBER_DOCTYPES = {
    "queries": "Insights Query v3",
    "charts": "Insights Chart v3",
    "dashboards": "Insights Dashboard v3",
}


def standard_dashboard_visibility() -> dict:
    """Who may read a dashboard an app ships.

    Desk User is frappe's automatic role for every System User, so the list
    never needs maintaining and the portal users, whose roles read their own
    orders and invoices, stay out of desk content.
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
        # a fixture or export written while this doctype was still `autoincrement` carries a
        # numeric name, and the column is varchar now — `validate_name` throws on an int
        if isinstance(self.name, int):
            self.name = str(self.name)

    def autoname(self):
        # plain numbers, carrying on from where `autoincrement` left off — see
        # insights/patches/name_workbooks_as_strings.py for why this needs to be a string.
        self.name = getseries(WORKBOOK_SERIES_KEY, 1)

    def validate(self):
        standard.validate_standard(self)

        # a module ties the workbook to the app that ships it; a site's own
        # workbook belongs to no app
        if self.is_standard and not self.module:
            frappe.throw(frappe._("A standard workbook must name the module it ships in."))

        # `module` is a Link to `Module Def`, which holds a site's own modules
        # too, and the framework reads shipped files back from installed apps'
        # `modules.txt` alone. Asked here rather than in `mark_as_standard`, so
        # a plain save, a bench console and the workbook CLI are covered by the
        # one condition.
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
            # the claim belongs to every path that decides a standard workbook's
            # name, not only to `mark_as_standard`: two names scrub to one
            # filename, and `after_rename` below would write the loser's file
            # away - leaving a workbook the next migrate deletes as an orphan
            standard.claim_file(self.doctype, new_name, self.module)

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
            # dashboards before charts, so a chart's delete finds no dashboard of
            # this workbook to take its cells off
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
        """Refuse the delete while a desk document draws one of its members.

        The members go with `force=True`, which skips the link check each one's
        own delete is refused by. A forced workbook delete skips it too, as
        frappe's own check does, so a re-sync is never blocked.
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
        """Restore the members the file carries, under the names it gives them.

        The counterpart of `before_export`. `import_doc` builds the workbook from
        the whole file, so the members ride on the document as attributes that
        are not fields. A standard workbook is the same document on every site,
        so nothing here is re-keyed.
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

        The map is keyed on the name the file carries and valued on the name the
        copy got, so a caller can reach what it just imported.

        `keep_names` restores the file as written: a member is inserted under the
        name the file gives it, one the site already holds is updated in place, and
        the members the file no longer carries are deleted. That is how a standard
        workbook arrives. Every other restore mints fresh names and rewrites the
        references that name them.
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

        # kept out of `id_map`: a folder is named by its title and a member by
        # its docname, and one dict for both makes a folder titled like a query
        # take that query's slot
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
                # the file never carries this: a hand-edited one cannot hand a
                # standard chart everyone's rows
                chart["run_as_owner"] = 0

            id_map[name] = _restore_member(
                "Insights Chart v3", name, chart, target_workbook_name, keep_names, ignore_permissions
            )

        for name, dashboard in dashboards.items():
            dashboard = deep_convert_dict_to_dict(dashboard)
            dashboard["items"] = frappe.as_json(_rewrite_dashboard_items(dashboard.get("items"), id_map))
            if keep_names:
                # the file never carries these: a hand-edited one cannot shut a
                # shipped board away from the desk users it ships for
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
        """The workbook and its members, in the shape a file carries them.

        One format for the download, Duplicate, the backup a delete leaves behind
        and the file an app ships.
        """
        return {
            "doctype": self.doctype,
            "name": self.name,
            "title": self.title,
            **self.export_members(),
        }

    def before_export(self, doc_export: dict) -> None:
        """Add the members to the file frappe is about to write.

        `as_dict` puts a summary of each member list on the document for the
        frontend's sidebar; the file carries the members themselves instead. A
        member kept for desk is no longer the app's, so it is left out.
        """
        doc_export.update(self.export_members(shipped=True))
        for field in ("read_only", "data_backup"):
            doc_export.pop(field, None)

    def export_members(self, shipped: bool = False) -> dict:
        """The workbook's queries, charts, dashboards and folders; with `shipped`,
        only those its app ships.

        A member names its folder by title. The folder's own name is a hash, which
        the importing site mints for itself.
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

        # only the folders that hold a query or a chart
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
        """Hand this workbook to the app that ships `module`, and answer with its name.

        The names become the workbook's identity on every site that takes the
        file, so they are readable and they are settled here, once: the workbook
        takes `name`, a member takes `<workbook>-<title slug>`, and every
        reference inside `operations`, `items` and a filter's `links` is
        rewritten to match.
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

        standard.claim_file(self.doctype, name, module)

        if name != self.name:
            rename_doc(self.doctype, self.name, name, force=True, ignore_permissions=True)
        renames = _rename_members(name)

        for doctype, old, new in renames:
            rename_doc(doctype, old, new, force=True, ignore_permissions=True)

        id_map = {old: new for _, old, new in renames}
        _rewrite_member_references(name, id_map)

        # the workbook first: a member reads its own `is_standard` off this row
        workbook = frappe.get_doc(self.doctype, name)
        workbook.is_standard = 1
        workbook.module = module
        workbook.save()

        # the dashboards next: a chart on a Public one cannot run as its
        # reader, and a shipped chart has to
        for dashboard in frappe.get_all("Insights Dashboard v3", {"workbook": name}, pluck="name"):
            doc = frappe.get_doc("Insights Dashboard v3", dashboard)
            doc.update(standard_dashboard_visibility())
            doc.save(ignore_permissions=True)
        # through the document: `run_as_owner` decides whose rows every
        # reader of the chart gets, and `validate_run_as_owner` is what
        # says a shipped chart runs as its reader
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
    graph, so such an order exists. A file with no such order carries a cycle.
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
    """The name each member takes, as `<workbook>-<title slug>`.

    Two members can carry one title, and another document may already answer to
    the name, so a taken one gets a number.
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
    """Whether a document other than `member` already answers to `name`.

    A dashboard answers to its route as well as to its docname, and
    `resolver.resolve` tries the docname first, so the two draw from one
    keyspace. Minting a member's docname over a site dashboard's route takes
    over every link that used that route, and the re-save that follows does not
    free it - `set_route` only re-derives the shipped dashboard's own.

    `InsightsDashboardv3.answered_by_another` is that pair of lookups, asked
    here rather than restated: this is the other writer into the one keyspace.
    """
    if doctype == MEMBER_DOCTYPES["dashboards"]:
        return frappe.get_doc(doctype, member).answered_by_another(name)

    return name != member and bool(frappe.db.exists(doctype, name))


def _rewrite_member_references(workbook: str, id_map: dict) -> None:
    """Point every reference inside a member's JSON at the name it took.

    `rename_doc` carries the Link fields; a name inside `operations` or a
    dashboard's `items` is not one.

    A member the rename left alone is still one of the workbook's own, and a
    reference to it names the workbook as well, so it stands in the map under
    its own name.
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
    """Whether a file is one `workbook_contents` reads.

    A file names itself by the doctype it was written from, or, in the wrapped
    shape, as a `Workbook`.
    """
    try:
        data = frappe.parse_json(workbook_data)
    except ValueError:
        return False
    return isinstance(data, dict) and (
        data.get("doctype") == "Insights Workbook" or data.get("type") == "Workbook"
    )


def workbook_contents(workbook_data) -> "frappe._dict":
    """A workbook file, with its members at the top.

    The format wrapped the workbook in `doc` and its members in `dependencies`
    before it was flattened. A file in that shape is lifted here, so one reader
    serves both — the files an app ships and every file a site exported until now.
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
    """Give every folder in the file a folder on this site, keyed as the file names it.

    A file names a folder by title; one written before that names it by the hash
    the exporting site minted. The members use whichever the file wrote, so both
    are keys here.

    Keyed by `(type, title)`, because that is what a folder is unique by — a
    query folder and a chart folder may share a title, and a member reads the map
    with the type it is.
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
    """Restore one member and answer with the name it took."""
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
    """A row another workbook holds is not this file's to write into.

    Under `keep_names` this is an import, and the name comes off a file. A
    member is named `<workbook>-<title slug>`, deduped on the bench that wrote
    the file and nowhere else, so a site that installs two apps can hold a
    collision neither authoring bench could see. Reusing the row re-parents the
    other app's chart into this workbook, and the dashboard that still names it
    draws that chart with nothing on screen saying so.

    A dashboard answers to its route as well as to its docname, so a name no row
    holds can still be an address a site dashboard answers to - and
    `resolver.resolve` tries the docname first, so inserting under it takes over
    every link that used that route. `_rename_members` asks this on the bench
    that mints the name; the receiving site is the only place a collision
    between two apps is visible, so it asks it too.

    The refusal frappe's `validate_overwrite` gives for the workbook itself.
    Insights restores the members, so it owes the same one here.
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
    """The dashboard that answers to `name` as its route, if one does."""
    if doctype != MEMBER_DOCTYPES["dashboards"]:
        return None

    return frappe.db.get_value(doctype, {"route": name, "name": ("!=", name)}, "name")


def _delete_dropped_members(workbook: str, contents: dict) -> None:
    """Delete the members of `workbook` the file no longer carries.

    A member a desk document draws stays, with what it reads, and the keep is
    logged: deleting it would leave the desk document linking nothing, and
    refusing would block the migrate. A kept member is marked `kept_for_desk`,
    so the file is written without it. Dashboards first, so a chart is gone from
    every grid before it goes, and folders last, so nothing still sits in one.
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
    carried = {(folder["type"], folder["title"]) for folder in contents["folders"]}
    for folder in frappe.get_all(
        "Insights Folder", filters={"workbook": workbook}, fields=["name", "title", "type"]
    ):
        if (folder.type, folder.title) not in carried and folder.name not in kept_folders:
            frappe.delete_doc("Insights Folder", folder.name, force=True, ignore_permissions=True)


def _kept_for_desk(workbook: str, dropped: dict) -> set[str]:
    """The dropped members a desk document draws, the charts a kept dashboard
    draws, and the queries they read."""
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

    # every migrate re-checks a kept member, so only a new keep is logged
    already_kept = {
        name
        for doctype in MEMBER_DOCTYPES.values()
        for name in frappe.get_all(doctype, filters={"workbook": workbook, "kept_for_desk": 1}, pluck="name")
    }
    newly_claimed = [claim for claim in claims if claim[2] not in already_kept]
    if newly_claimed:
        frappe.log_error(
            title=f"Kept what a desk document draws in {workbook}",
            message="\n".join(
                f"{desk_doctype} {desk_name} draws {claimed}, which the file no longer carries"
                for desk_doctype, desk_name, claimed in newly_claimed
            ),
        )
    return kept


def delete_unclaimed_kept_members() -> None:
    """Delete what a re-sync kept for desk once no desk document draws it.

    frappe re-imports a file only when it changes, so without this a kept member
    would stay, read-only, until the app next changed that file.
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
    """Point every chart and filter link in `items` at the copy that replaces it."""
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

    A reference names the query it reads and the workbook that query sits in, so
    both move together: `workbook` is the one the copies belong to.

    A name the map does not carry belongs to a query already on this site, and
    is left alone: the import references that one, and read access decides.
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
