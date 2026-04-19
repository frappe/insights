# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now

from insights.api.telemetry import capture_event
from insights.utils import deep_convert_dict_to_dict


class InsightsWorkbook(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        data_backup: DF.JSON | None
        name: DF.Int | None
        title: DF.Data
    # end: auto-generated types

    def before_save(self):
        self.title = self.title or f"Workbook {frappe.utils.cint(self.name)}"

    def on_trash(self):
        try:
            backup_data = frappe.as_json(self.export())
            self.db_set("data_backup", backup_data)
        except Exception as e:
            frappe.log_error(f"Failed to backup workbook {self.name}: {e!s}")

        for q in frappe.get_all("Insights Query v3", {"workbook": self.name}):
            frappe.delete_doc("Insights Query v3", q.name, force=True, ignore_permissions=True)
        for c in frappe.get_all("Insights Chart v3", {"workbook": self.name}):
            frappe.delete_doc("Insights Chart v3", c.name, force=True, ignore_permissions=True)
        for d in frappe.get_all("Insights Dashboard v3", {"workbook": self.name}):
            frappe.delete_doc("Insights Dashboard v3", d.name, force=True, ignore_permissions=True)
        for f in frappe.get_all("Insights Folder", {"workbook": self.name}):
            frappe.delete_doc("Insights Folder", f.name, force=True, ignore_permissions=True)

    def after_insert(self):
        capture_event("workbook_created")

        # If this is a restored workbook (has data_backup) then restore child documents
        if not self.data_backup:
            # This is a normal new workbook and not a restored one(skip restore)
            return

        # Parse backup data
        backup = frappe.parse_json(self.data_backup)
        backup = deep_convert_dict_to_dict(backup)

        self.restore_workbook_contents(backup, self.name, ignore_permissions=True)
        self.db_set("data_backup", None)

    def restore_workbook_contents(self, workbook_data, target_workbook_name, ignore_permissions=False):
        """
        Shared method to restore/import workbook contents
        """
        old_workbook_name = workbook_data.get("name")

        # Create ID mapping
        id_map = {old_workbook_name: target_workbook_name}

        # Restore logic
        for folder in workbook_data.get("dependencies", {}).get("folders", []):
            folder = deep_convert_dict_to_dict(folder)
            old_folder_name = folder["name"]
            new_folder = frappe.new_doc("Insights Folder")
            new_folder.title = folder["title"]
            new_folder.type = folder["type"]
            new_folder.sort_order = folder["sort_order"]
            new_folder.workbook = target_workbook_name
            new_folder.insert(ignore_permissions=ignore_permissions)
            id_map[old_folder_name] = new_folder.name

        query_sort_order = 0
        for name, query in workbook_data.get("dependencies", {}).get("queries", {}).items():
            query = deep_convert_dict_to_dict(query)
            new_query = frappe.new_doc("Insights Query v3")
            new_query.update(query)
            new_query.workbook = target_workbook_name

            if query.get("folder") and query.get("folder") in id_map:
                new_query.folder = id_map[query.get("folder")]

            if not hasattr(new_query, "sort_order") or new_query.sort_order is None:
                new_query.sort_order = query_sort_order
                query_sort_order += 1

            new_query.insert(ignore_permissions=ignore_permissions)
            id_map[name] = new_query.name

        for name, _ in workbook_data.get("dependencies", {}).get("queries", {}).items():
            new_query = frappe.get_doc("Insights Query v3", id_map[name])
            operations = deep_convert_dict_to_dict(frappe.parse_json(new_query.operations))

            should_update = False
            for op in operations:
                if (
                    not op.get("table")
                    or not op.get("table").get("type")
                    or not op.get("table").get("query_name")
                ):
                    continue

                ref_query = op.table.query_name
                if ref_query in id_map:
                    op.table.query_name = id_map[ref_query]
                    should_update = True

            if should_update:
                new_query.db_set("operations", frappe.as_json(operations))

        chart_sort_order = 0
        for name, chart in workbook_data.get("dependencies", {}).get("charts", {}).items():
            chart = deep_convert_dict_to_dict(chart)
            new_chart = frappe.new_doc("Insights Chart v3")
            new_chart.update(chart)
            new_chart.workbook = target_workbook_name

            if chart.get("query") and chart.get("query") in id_map:
                new_chart.query = id_map[chart.get("query")]

            if chart.get("folder") and chart.get("folder") in id_map:
                new_chart.folder = id_map[chart.get("folder")]

            if not hasattr(new_chart, "sort_order") or new_chart.sort_order is None:
                new_chart.sort_order = chart_sort_order
                chart_sort_order += 1

            new_chart.insert(ignore_permissions=ignore_permissions)
            id_map[name] = new_chart.name

        for _, dashboard in workbook_data.get("dependencies", {}).get("dashboards", {}).items():
            dashboard = deep_convert_dict_to_dict(dashboard)
            new_dashboard = frappe.new_doc("Insights Dashboard v3")
            new_dashboard.update(dashboard)
            new_dashboard.workbook = target_workbook_name

            items = deep_convert_dict_to_dict(frappe.parse_json(dashboard["items"]))
            for item in items:
                if item.get("type") == "chart" and item.get("chart") and item.get("chart") in id_map:
                    item["chart"] = id_map.get(item["chart"])

                if item.get("type") == "filter" and item.get("links"):
                    new_links = {}
                    for chart_name, field in item["links"].items():
                        if chart_name not in id_map or not field or "`.`" not in field:
                            continue

                        chart = id_map[chart_name]
                        field_query = field.split("`.`")[0].replace("`", "")
                        field_name = field.split("`.`")[1].replace("`", "")

                        if field_query not in id_map:
                            continue

                        query_name = id_map[field_query]
                        new_links[chart] = f"`{query_name}`.`{field_name}`"

                    item["links"] = new_links

            new_dashboard.items = frappe.as_json(items)
            new_dashboard.insert(ignore_permissions=ignore_permissions)

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

        chart_queries = frappe.get_all(
            "Insights Chart v3",
            filters={"workbook": self.name},
            pluck="data_query",
        )
        d.queries = frappe.get_all(
            "Insights Query v3",
            filters={
                "workbook": self.name,
                "name": ["not in", chart_queries],
            },
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
        d.read_only = not self.has_permission("write")
        return d

    @frappe.whitelist()
    def track_view(self):
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

    @frappe.whitelist()
    def export(self):
        workbook = {
            "version": "1.0",
            "timestamp": frappe.utils.now(),
            "type": "Workbook",
            "name": self.name,
            "doc": {
                "name": self.name,
                "title": self.title,
            },
            "dependencies": {
                "folders": [],
                "queries": {},
                "charts": {},
                "dashboards": {},
            },
        }

        chart_queries = frappe.get_all("Insights Chart v3", {"workbook": self.name}, pluck="data_query")
        queries = frappe.get_all(
            "Insights Query v3",
            filters={
                "workbook": self.name,
                "name": ["not in", chart_queries],
            },
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
        for q in queries:
            q.operations = frappe.parse_json(q.operations)
            workbook["dependencies"]["queries"][q.name] = q

        charts = frappe.get_all(
            "Insights Chart v3",
            filters={"workbook": self.name},
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
        for c in charts:
            c.config = frappe.parse_json(c.config)
            workbook["dependencies"]["charts"][c.name] = c

        # Export only folders that have active queries or charts
        query_folders = set([q.get("folder") for q in queries if q.get("folder")])
        chart_folders = set([c.get("folder") for c in charts if c.get("folder")])
        active_folders = query_folders | chart_folders

        if active_folders:
            workbook["dependencies"]["folders"] = frappe.get_all(
                "Insights Folder",
                filters={"workbook": self.name, "name": ["in", list(active_folders)]},
                fields=[
                    "name",
                    "title",
                    "type",
                    "sort_order",
                ],
                order_by="sort_order asc, creation asc",
            )
        else:
            workbook["dependencies"]["folders"] = []

        dashboards = frappe.get_all(
            "Insights Dashboard v3",
            filters={"workbook": self.name},
            fields=[
                "name",
                "title",
                "workbook",
                "items",
            ],
            order_by="creation asc",
        )
        for d in dashboards:
            d["items"] = frappe.parse_json(d["items"])
            workbook["dependencies"]["dashboards"][d.name] = d

        return workbook

    @frappe.whitelist()
    def duplicate(self):
        workbook = self.export()
        workbook["doc"]["title"] = None
        return import_workbook(workbook)

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

        chart_query_map: dict[str, str] = {
            row.data_query: row.title
            for row in frappe.get_all(
                "Insights Chart v3",
                filters={"workbook": self.name, "data_query": ("is", "set")},
                fields=["data_query", "title"],
            )
        }
        for node in nodes.values():
            if node["node_type"] == "query" and node["name"] in chart_query_map:
                node["is_chart_query"] = True
                node["chart_title"] = chart_query_map[node["name"]]

        return {
            "nodes": list(nodes.values()),
            "edges": edge_list,
        }


def import_workbook(workbook):
    workbook = frappe.parse_json(workbook)
    workbook = deep_convert_dict_to_dict(workbook)

    # Create a new Insights Workbook
    new_workbook = frappe.new_doc("Insights Workbook")
    new_workbook.title = workbook["doc"]["title"]
    new_workbook.insert()
    new_workbook.restore_workbook_contents(
        workbook,
        new_workbook.name,
    )

    return new_workbook.name
