# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import cint

from insights.utils import InsightsChart, InsightsTable


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
    def fetch_table_meta(self):
        if not self.is_assisted_query:
            return []

        tables = self.variant_controller.get_selected_tables()
        table_names = [table["table"] for table in tables if table["table"]]
        if not table_names:
            return []
        return SchemaGenerator(self.data_source, table_names).generate()


class SchemaGenerator:
    def __init__(self, data_source, table_names):
        self.data_source = data_source
        self.table_names = table_names
        self._tables = {}

    def generate(self):
        schema = {}
        for table_name in self.table_names:
            if schema.get(table_name):
                continue
            schema[table_name] = self.get_schema(table_name)
            for table_link in schema[table_name]["relations"]:
                if table_link["foreign_table"] not in schema:
                    schema[table_link["foreign_table"]] = self.get_schema(
                        table_link["foreign_table"]
                    )
        return schema.values()

    def get_schema(self, table_name):
        table = self.get_table(table_name)
        return frappe._dict(
            {
                "table": table_name,
                "label": table.label,
                "data_source": table.data_source,
                "columns": self.get_table_columns(table_name),
                "relations": self.get_table_relations(table_name),
            }
        )

    def get_table(self, table_name):
        if table_name not in self._tables:
            self._tables[table_name] = self._fetch_table(table_name)
        return self._tables[table_name]

    def _fetch_table(self, table_name):
        return InsightsTable.get_doc(
            {
                "data_source": self.data_source,
                "table": table_name,
            }
        )

    def get_table_columns(self, table_name):
        table = self.get_table(table_name)
        return [
            {
                "column": column.column,
                "type": column.type,
                "label": column.label,
                "table": table_name,
                "table_label": table.label,
                "data_source": table.data_source,
            }
            for column in table.columns
        ]

    def get_table_relations(self, table_name):
        table = self.get_table(table_name)
        return [
            {
                "primary_table": table_name,
                "primary_column": relation.primary_key,
                "foreign_table": relation.foreign_table,
                "foreign_column": relation.foreign_key,
                "cardinality": relation.cardinality,
            }
            for relation in table.table_links
        ]
