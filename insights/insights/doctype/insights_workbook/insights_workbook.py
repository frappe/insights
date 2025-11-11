# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import frappe.utils
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now

from insights.utils import deep_convert_dict_to_dict


class InsightsWorkbook(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        data_backup: DF.JSON | None
        enable_snapshots: DF.Check
        name: DF.Int | None
        title: DF.Data
    # end: auto-generated types

    def before_save(self):
        self.title = self.title or f"Workbook {frappe.utils.cint(self.name)}"

    def on_trash(self):
        to_delete = [
            "Insights Query v3",
            "Insights Chart v3",
            "Insights Dashboard v3",
            "Insights Folder",
            "Insights Workbook Snapshot",
        ]
        for doctype in to_delete:
            for item in frappe.get_all(doctype, {"workbook": self.name}):
                frappe.delete_doc(doctype, item.name, force=True, ignore_permissions=True)

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

        d.snapshots = frappe.get_all(
            "Insights Workbook Snapshot",
            filters={"workbook": self.name},
            fields=["name", "title"],
            order_by="creation desc",
        )

        d.folders = frappe.as_json(d.folders)
        d.queries = frappe.as_json(d.queries)
        d.charts = frappe.as_json(d.charts)
        d.dashboards = frappe.as_json(d.dashboards)
        d.snapshots = frappe.as_json(d.snapshots)

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
            order_by="sort_order asc, creation asc",
        )
        for idx, q in enumerate(queries):
            q.operations = frappe.parse_json(q.operations)
            q.sort_order = idx
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
            order_by="sort_order asc, creation asc",
        )
        for idx, c in enumerate(charts):
            c.config = frappe.parse_json(c.config)
            c.sort_order = idx
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
    def import_query(self, query):
        from insights.insights.doctype.insights_query_v3.insights_query_v3 import import_query

        return import_query(query, self.name)

    @frappe.whitelist()
    def import_chart(self, chart):
        from insights.insights.doctype.insights_chart_v3.insights_chart_v3 import import_chart

        return import_chart(chart, self.name)

    @frappe.whitelist()
    def save_snapshot(self, snapshot_name=None):
        """Save a snapshot of the current workbook state"""
        if not self.has_permission("write"):
            frappe.throw("You do not have permission to save snapshots for this workbook")

        snapshot = self.export()

        snapshot = frappe.new_doc("Insights Workbook Snapshot")
        snapshot.workbook = self.name
        snapshot.title = snapshot_name or f"Snapshot {frappe.utils.now()}"
        snapshot.snapshot = frappe.as_json(snapshot)

        try:
            snapshot.insert()
            return snapshot.name
        except frappe.ValidationError as e:
            # If validation fails due to no changes, return None gracefully
            if "No changes detected" in str(e):
                return None
            raise

    @frappe.whitelist()
    def get_snapshots(self):
        """Get all snapshots for this workbook"""
        if not self.has_permission("read"):
            frappe.throw("You do not have permission to view snapshots for this workbook")

        snapshots = frappe.get_all(
            "Insights Workbook Snapshot",
            filters={"workbook": self.name},
            fields=["name", "title", "creation", "owner"],
            order_by="creation desc",
        )

        return snapshots

    @frappe.whitelist()
    def restore_snapshot(self, snapshot_name):
        """Restore workbook from a snapshot"""
        if not self.has_permission("write"):
            frappe.throw("You do not have permission to restore snapshots for this workbook")

        # Fetch and validate snapshot
        snapshot = frappe.get_doc("Insights Workbook Snapshot", snapshot_name)
        if str(snapshot.workbook) != str(self.name):
            frappe.throw("This snapshot does not belong to the current workbook")

        # Restore from snapshot (updates existing items, creates new ones, deletes extras)
        snapshot_data = frappe.parse_json(snapshot.snapshot)
        restore_workbook_from_snapshot(self, snapshot_data)

        return {"success": True, "message": "Workbook restored successfully"}


def import_workbook(workbook):
    workbook = frappe.parse_json(workbook)
    workbook = deep_convert_dict_to_dict(workbook)

    # Create a new Insights Workbook
    new_workbook = frappe.new_doc("Insights Workbook")
    new_workbook.title = workbook["doc"]["title"]
    new_workbook.insert()

    # Populate the workbook with data (creates all new items)
    _populate_workbook(new_workbook, workbook, preserve_existing=False)

    return new_workbook.name


def restore_workbook_from_snapshot(existing_workbook, snapshot_data):
    """Restore a workbook from snapshot data, preserving the workbook ID and updating existing items"""
    snapshot_data = frappe.parse_json(snapshot_data)
    snapshot_data = deep_convert_dict_to_dict(snapshot_data)

    # Populate the workbook with data (updates existing items, creates new ones, deletes extras)
    _populate_workbook(existing_workbook, snapshot_data, preserve_existing=True)


def _populate_workbook(workbook, workbook_data, preserve_existing=False):
    """
    Populate a workbook with data from workbook_data.
    If preserve_existing is True, updates existing items and deletes items not in workbook_data.
    If preserve_existing is False, creates all new items with new IDs.
    """
    # Get existing items if we need to preserve them
    existing_items = _get_existing_workbook_items(workbook.name) if preserve_existing else {}

    # Track which items are in the snapshot
    snapshot_items = {
        "folders": set(),
        "queries": set(),
        "charts": set(),
        "dashboards": set(),
    }

    # Map old IDs to new IDs
    id_map = {}

    # Process each entity type
    _process_folders(
        workbook,
        workbook_data,
        preserve_existing,
        existing_items.get("folders", {}),
        snapshot_items["folders"],
        id_map,
    )
    _process_queries(
        workbook,
        workbook_data,
        preserve_existing,
        existing_items.get("queries", {}),
        snapshot_items["queries"],
        id_map,
    )
    _update_query_references(snapshot_items["queries"], id_map)
    _process_charts(
        workbook,
        workbook_data,
        preserve_existing,
        existing_items.get("charts", {}),
        snapshot_items["charts"],
        id_map,
    )
    _process_dashboards(
        workbook,
        workbook_data,
        preserve_existing,
        existing_items.get("dashboards", {}),
        snapshot_items["dashboards"],
        id_map,
    )

    # Delete items not in snapshot
    if preserve_existing:
        _delete_removed_items(existing_items, snapshot_items)


def _get_existing_workbook_items(workbook_name):
    """Get all existing items in a workbook"""
    return {
        "folders": {
            f.name: f for f in frappe.get_all("Insights Folder", {"workbook": workbook_name}, ["name"])
        },
        "queries": {
            q.name: q for q in frappe.get_all("Insights Query v3", {"workbook": workbook_name}, ["name"])
        },
        "charts": {
            c.name: c for c in frappe.get_all("Insights Chart v3", {"workbook": workbook_name}, ["name"])
        },
        "dashboards": {
            d.name: d for d in frappe.get_all("Insights Dashboard v3", {"workbook": workbook_name}, ["name"])
        },
    }


def _process_folders(
    workbook, workbook_data, preserve_existing, existing_folders, snapshot_folder_names, id_map
):
    """Process folders - update existing or create new"""
    for folder in workbook_data.get("dependencies", {}).get("folders", []):
        folder = deep_convert_dict_to_dict(folder)
        old_folder_name = folder["name"]
        snapshot_folder_names.add(old_folder_name)

        if preserve_existing and old_folder_name in existing_folders:
            # Update existing folder
            folder_doc = frappe.get_doc("Insights Folder", old_folder_name)
            folder_doc.title = folder["title"]
            folder_doc.type = folder["type"]
            folder_doc.sort_order = folder.get("sort_order", 0)
            folder_doc.save()
            id_map[old_folder_name] = old_folder_name
        else:
            # Create new folder (with original name if preserve_existing)
            new_folder = frappe.new_doc("Insights Folder")
            new_folder.title = folder["title"]
            new_folder.type = folder["type"]
            new_folder.sort_order = folder.get("sort_order", 0)
            new_folder.workbook = workbook.name
            if preserve_existing:
                new_folder.insert(set_name=old_folder_name)
            else:
                new_folder.insert()
            id_map[old_folder_name] = new_folder.name


def _process_queries(
    workbook, workbook_data, preserve_existing, existing_queries, snapshot_query_names, id_map
):
    """Process queries - update existing or create new"""
    query_sort_order = 0
    for name, query in workbook_data.get("dependencies", {}).get("queries", {}).items():
        query = deep_convert_dict_to_dict(query)
        snapshot_query_names.add(name)

        if preserve_existing and name in existing_queries:
            # Update existing query
            query_doc = frappe.get_doc("Insights Query v3", name)
            query_doc.title = query.get("title")
            query_doc.is_builder_query = query.get("is_builder_query")
            query_doc.is_native_query = query.get("is_native_query")
            query_doc.is_script_query = query.get("is_script_query")
            query_doc.use_live_connection = query.get("use_live_connection")
            query_doc.operations = query.get("operations")
            query_doc.folder = id_map.get(query.get("folder")) if query.get("folder") else None
            query_doc.sort_order = query.get("sort_order", query_sort_order)
            query_doc.save()
            id_map[name] = name
        else:
            # Create new query (with original name if preserve_existing)
            new_query = frappe.new_doc("Insights Query v3")
            new_query.update(query)
            new_query.workbook = workbook.name
            if query.get("folder") and query.get("folder") in id_map:
                new_query.folder = id_map[query.get("folder")]
            new_query.sort_order = query.get("sort_order", query_sort_order)
            if preserve_existing:
                new_query.insert(set_name=name)
            else:
                new_query.insert()
            id_map[name] = new_query.name

        query_sort_order += 1


def _update_query_references(snapshot_query_names, id_map):
    """Update query references in operations to use new IDs"""
    for name in snapshot_query_names:
        actual_name = id_map.get(name, name)
        query_doc = frappe.get_doc("Insights Query v3", actual_name)
        operations = deep_convert_dict_to_dict(frappe.parse_json(query_doc.operations))

        should_update = False
        for op in operations:
            if (
                not op.get("table")
                or not op.get("table").get("type")
                or not op.get("table").get("query_name")
            ):
                continue

            ref_query = op.get("table", {}).get("query_name")
            if ref_query in id_map and id_map[ref_query] != ref_query:
                op["table"]["query_name"] = id_map[ref_query]
                should_update = True

        if should_update:
            query_doc.db_set(
                "operations",
                frappe.as_json(operations),
                update_modified=False,
            )


def _process_charts(
    workbook, workbook_data, preserve_existing, existing_charts, snapshot_chart_names, id_map
):
    """Process charts - update existing or create new"""
    chart_sort_order = 0
    for name, chart in workbook_data.get("dependencies", {}).get("charts", {}).items():
        chart = deep_convert_dict_to_dict(chart)
        snapshot_chart_names.add(name)

        if preserve_existing and name in existing_charts:
            # Update existing chart
            chart_doc = frappe.get_doc("Insights Chart v3", name)
            chart_doc.title = chart.get("title")
            chart_doc.chart_type = chart.get("chart_type")
            chart_doc.config = chart.get("config")
            chart_doc.query = id_map.get(chart.get("query"), chart.get("query"))
            chart_doc.data_query = None  # Clear to let before_save() recreate it
            chart_doc.folder = id_map.get(chart.get("folder")) if chart.get("folder") else None
            chart_doc.sort_order = chart.get("sort_order", chart_sort_order)
            chart_doc.save()
            id_map[name] = name
        else:
            # Create new chart (with original name if preserve_existing)
            new_chart = frappe.new_doc("Insights Chart v3")
            new_chart.update(chart)
            new_chart.workbook = workbook.name
            if chart.get("query") and chart.get("query") in id_map:
                new_chart.query = id_map[chart.get("query")]
            if chart.get("folder") and chart.get("folder") in id_map:
                new_chart.folder = id_map[chart.get("folder")]
            new_chart.sort_order = chart.get("sort_order", chart_sort_order)
            if preserve_existing:
                new_chart.insert(set_name=name)
            else:
                new_chart.insert()
            id_map[name] = new_chart.name

        chart_sort_order += 1


def _process_dashboards(
    workbook, workbook_data, preserve_existing, existing_dashboards, snapshot_dashboard_names, id_map
):
    """Process dashboards - update existing or create new"""
    for name, dashboard in workbook_data.get("dependencies", {}).get("dashboards", {}).items():
        dashboard = deep_convert_dict_to_dict(dashboard)
        snapshot_dashboard_names.add(name)

        # Update dashboard items with new IDs
        items = deep_convert_dict_to_dict(frappe.parse_json(dashboard.get("items", [])))
        _update_dashboard_item_references(items, id_map)

        if preserve_existing and name in existing_dashboards:
            # Update existing dashboard
            dashboard_doc = frappe.get_doc("Insights Dashboard v3", name)
            dashboard_doc.title = dashboard.get("title")
            dashboard_doc.items = frappe.as_json(items)
            dashboard_doc.save()
            id_map[name] = name
        else:
            # Create new dashboard (with original name if preserve_existing)
            new_dashboard = frappe.new_doc("Insights Dashboard v3")
            new_dashboard.update(dashboard)
            new_dashboard.workbook = workbook.name
            new_dashboard.items = frappe.as_json(items)
            if preserve_existing:
                new_dashboard.insert(set_name=name)
            else:
                new_dashboard.insert()
            id_map[name] = new_dashboard.name


def _update_dashboard_item_references(items, id_map):
    """Update chart and query references in dashboard items"""
    for item in items:
        if item.get("type") == "chart" and item.get("chart"):
            item["chart"] = id_map.get(item.get("chart"), item.get("chart"))

        if item.get("type") == "filter" and item.get("links"):
            new_links = {}
            for chart_name, field in item.get("links", {}).items():
                if not field or "`.`" not in field:
                    continue

                mapped_chart = id_map.get(chart_name, chart_name)
                field_parts = field.split("`.`")
                if len(field_parts) >= 2:
                    field_query = field_parts[0].replace("`", "")
                    field_name = field_parts[1].replace("`", "")
                    mapped_query = id_map.get(field_query, field_query)
                    new_links[mapped_chart] = f"`{mapped_query}`.`{field_name}`"

            item["links"] = new_links


def _delete_removed_items(existing_items, snapshot_items):
    """Delete items that are not in the snapshot"""
    for folder_name in existing_items.get("folders", {}):
        if folder_name not in snapshot_items["folders"]:
            frappe.delete_doc("Insights Folder", folder_name, ignore_permissions=True)

    for query_name in existing_items.get("queries", {}):
        if query_name not in snapshot_items["queries"]:
            frappe.delete_doc("Insights Query v3", query_name, ignore_permissions=True)

    for chart_name in existing_items.get("charts", {}):
        if chart_name not in snapshot_items["charts"]:
            frappe.delete_doc("Insights Chart v3", chart_name, ignore_permissions=True)

    for dashboard_name in existing_items.get("dashboards", {}):
        if dashboard_name not in snapshot_items["dashboards"]:
            frappe.delete_doc("Insights Dashboard v3", dashboard_name, ignore_permissions=True)
