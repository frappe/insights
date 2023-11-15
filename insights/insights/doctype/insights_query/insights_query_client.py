# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import cint

from insights.utils import InsightsChart, InsightsQuery, InsightsTable


class InsightsQueryClient:
    @frappe.whitelist()
    def duplicate(self):
        new_query = frappe.copy_doc(self)
        new_query.save()
        return new_query.name

    @frappe.whitelist()
    def add_transform(self, type, options):
        existing = self.get("transforms", {"type": type})
        if existing:
            existing[0].options = frappe.as_json(options)
        else:
            self.append(
                "transforms",
                {
                    "type": type,
                    "options": frappe.as_json(options),
                },
            )
        self.run()

    @frappe.whitelist()
    def reset_transforms(self):
        self.transforms = []
        self.run()

    @frappe.whitelist()
    def set_limit(self, limit):
        validated_limit = cint(limit)
        if not validated_limit or validated_limit < 0:
            frappe.throw("Limit must be a positive integer")
        self.limit = validated_limit
        self.save()

    @frappe.whitelist()
    def run(self):
        self.fetch_results()
        self.save()

    @frappe.whitelist()
    def reset_and_save(self):
        self.reset()
        self.save()

    @frappe.whitelist()
    def store(self):
        self.is_stored = 1
        self.save()

    @frappe.whitelist()
    def convert(self):
        self.is_native_query = not self.is_native_query
        self.save()

    @frappe.whitelist()
    def convert_to_native(self):
        if self.is_native_query:
            return
        self.is_native_query = 1
        self.save()

    @frappe.whitelist()
    def convert_to_assisted(self):
        if self.is_assisted_query:
            return
        self.is_assisted_query = 1
        self.save()

    @frappe.whitelist()
    def get_chart_name(self):
        chart_name = InsightsChart.get_name(query=self.name)
        if not chart_name:
            new_chart = self.create_default_chart()
            chart_name = new_chart.name
        return chart_name

    @frappe.whitelist()
    def save_as_table(self):
        return self.update_insights_table(force=True)

    @frappe.whitelist()
    def delete_linked_table(self):
        return self.delete_insights_table()

    @frappe.whitelist()
    def fetch_related_tables_columns(self, search_query=None):
        if search_query and not isinstance(search_query, str):
            frappe.throw("Search query must be a string")

        if not self.is_assisted_query:
            return []

        tables = self.variant_controller.get_selected_tables()
        table_names = [table["table"] for table in tables if table["table"]]
        if not table_names:
            return []

        related_table_names = get_related_table_names(table_names, self.data_source)

        insights_table = frappe.qb.DocType("Insights Table")
        insights_table_column = frappe.qb.DocType("Insights Table Column")

        fields_to_select = [
            insights_table_column.column,
            insights_table_column.label,
            insights_table_column.type,
            insights_table.table,
            insights_table.data_source,
            insights_table.label.as_("table_label"),
        ]

        search_cond = insights_table.name.isnotnull()
        if search_query:
            search_cond = (insights_table_column.column.like(f"%{search_query}%")) | (
                insights_table_column.label.like(f"%{search_query}%")
            )

        cols = (
            frappe.qb.from_(insights_table)
            .left_join(insights_table_column)
            .on(insights_table.name == insights_table_column.parent)
            .select(*fields_to_select)
            .where(
                (insights_table.data_source == self.data_source)
                & (search_cond)
                & (
                    insights_table.table.isin(related_table_names)
                    | insights_table.table.isin(table_names)
                )
            )
            .groupby(insights_table.table, insights_table_column.column)
            .limit(500)
            .run(as_dict=True)
        )

        columns = []
        for col in cols:
            col_added = any(
                col["column"] == column["column"] and col["table"] == column["table"]
                for column in columns
            )
            if col_added:
                continue
            columns.append(
                {
                    "column": col.column,
                    "label": col.label,
                    "type": col.type,
                    "table": col.table,
                    "table_label": col.table_label,
                    "data_source": col.data_source,
                }
            )

        return columns


def get_related_table_names(table_names, data_source):
    insights_table = frappe.qb.DocType("Insights Table")
    insights_table_link = frappe.qb.DocType("Insights Table Link")

    referenced_tables = (
        frappe.qb.from_(insights_table)
        .left_join(insights_table_link)
        .on(insights_table.name == insights_table_link.parent)
        .where(
            (insights_table.data_source == data_source) & (insights_table.table.isin(table_names))
        )
        .select(insights_table_link.foreign_table)
        .groupby(insights_table_link.foreign_table)
        .run(pluck=True)
    )
    referencing_tables = (
        frappe.qb.from_(insights_table)
        .left_join(insights_table_link)
        .on(insights_table.name == insights_table_link.parent)
        .where(
            (insights_table.data_source == data_source)
            & (insights_table_link.foreign_table.isin(table_names))
        )
        .select(insights_table.table)
        .groupby(insights_table.table)
        .run(pluck=True)
    )

    return list(set(referenced_tables + referencing_tables) - set(table_names))
