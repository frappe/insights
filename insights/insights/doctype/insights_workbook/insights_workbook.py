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
        name: DF.Int | None
        title: DF.Data
    # end: auto-generated types

    def before_save(self):
        self.title = self.title or f"Workbook {frappe.utils.cint(self.name)}"

    def on_trash(self):
        for q in frappe.get_all("Insights Query v3", {"workbook": self.name}):
            frappe.delete_doc("Insights Query v3", q.name, force=True, ignore_permissions=True)
        for c in frappe.get_all("Insights Chart v3", {"workbook": self.name}):
            frappe.delete_doc("Insights Chart v3", c.name, force=True, ignore_permissions=True)
        for d in frappe.get_all("Insights Dashboard v3", {"workbook": self.name}):
            frappe.delete_doc("Insights Dashboard v3", d.name, force=True, ignore_permissions=True)

    def as_dict(self, *args, **kwargs):
        d = super().as_dict(*args, **kwargs)
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
                "is_native_query",
                "is_builder_query",
                "is_script_query",
            ],
            order_by="creation asc",
        )
        d.charts = frappe.get_all(
            "Insights Chart v3",
            filters={"workbook": self.name},
            fields=[
                "name",
                "title",
                "chart_type",
                "query",
            ],
            order_by="creation asc",
        )
        d.dashboards = frappe.get_all(
            "Insights Dashboard v3",
            filters={"workbook": self.name},
            fields=["name", "title"],
            order_by="creation asc",
        )
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
                "queries": {},
                "charts": {},
                "dashboards": {},
            },
        }

        queries = frappe.get_all(
            "Insights Query v3",
            filters={
                "workbook": self.name,
                "name": [
                    "not in",
                    frappe.get_all("Insights Chart v3", {"workbook": self.name}, pluck="data_query"),
                ],
            },
            fields=[
                "name",
                "title",
                "workbook",
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
                "query",
                "chart_type",
                "config",
            ],
            order_by="creation asc",
        )
        for c in charts:
            c.config = frappe.parse_json(c.config)
            workbook["dependencies"]["charts"][c.name] = c

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


def import_workbook(workbook):
    workbook = frappe.parse_json(workbook)
    workbook = deep_convert_dict_to_dict(workbook)

    # Create a new Insights Workbook
    new_workbook = frappe.new_doc("Insights Workbook")
    new_workbook.title = workbook["doc"]["title"]
    new_workbook.insert()

    id_map = {}

    # Copy queries, charts, and dashboards
    for name, query in workbook.dependencies.queries.items():
        query = deep_convert_dict_to_dict(query)
        new_query = frappe.new_doc("Insights Query v3")
        new_query.update(query)
        new_query.workbook = new_workbook.name
        new_query.insert()
        id_map[name] = new_query.name

    # update old query names with new query names
    for name, _ in workbook.dependencies.queries.items():
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
            new_query.db_set(
                "operations",
                frappe.as_json(operations),
                update_modified=False,
            )

    for name, chart in workbook.dependencies.charts.items():
        chart = deep_convert_dict_to_dict(chart)
        new_chart = frappe.new_doc("Insights Chart v3")
        new_chart.update(chart)
        new_chart.workbook = new_workbook.name
        if chart.query in id_map:
            new_chart.query = id_map[chart.query]
        new_chart.insert()
        id_map[name] = new_chart.name

    for _, dashboard in workbook.dependencies.dashboards.items():
        dashboard = deep_convert_dict_to_dict(dashboard)
        new_dashboard = frappe.new_doc("Insights Dashboard v3")
        new_dashboard.update(dashboard)
        new_dashboard.workbook = new_workbook.name

        items = deep_convert_dict_to_dict(frappe.parse_json(dashboard["items"]))
        for item in items:
            if item.type == "chart" and item.chart and item.chart in id_map:
                item.chart = id_map.get(item.chart)

            if item.type == "filter" and item.links:
                new_links = {}

                for chart_name, field in item.links.items():
                    if chart_name not in id_map or not field or "`.`" not in field:
                        continue

                    chart = id_map[chart_name]
                    field_query = field.split("`.`")[0].replace("`", "")
                    field_name = field.split("`.`")[1].replace("`", "")

                    if field_query not in id_map:
                        continue

                    query_name = id_map[field_query]
                    new_links[chart_name] = f"`{query_name}`.`{field_name}`"

                item.links = new_links

        new_dashboard.items = frappe.as_json(items)
        new_dashboard.insert()

    return new_workbook.name
