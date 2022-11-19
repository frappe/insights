# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from copy import deepcopy
from json import dumps

import frappe
from frappe.utils import cint, cstr

from insights.api import get_tables


class InsightsQueryClient:
    @frappe.whitelist()
    def duplicate(self):
        new_query = frappe.copy_doc(self)
        new_query.save()
        return new_query.name

    @frappe.whitelist()
    def get_charts(self):
        return frappe.get_list(
            "Insights Query Chart",
            filters={"query": self.name},
            pluck="name",
        )

    @frappe.whitelist()
    def add_table(self, table):
        new_table = {
            "label": table.get("label"),
            "table": table.get("table"),
        }
        self.append("tables", new_table)
        self.save()

    @frappe.whitelist()
    def update_table(self, table):
        for row in self.tables:
            if row.get("name") != table.get("name"):
                continue

            if table.get("join"):
                row.join = dumps(
                    table.get("join"),
                    default=cstr,
                    indent=2,
                )
            else:
                row.join = ""

            self.save()
            return

    @frappe.whitelist()
    def remove_table(self, table):
        for row in self.tables:
            if row.get("name") == table.get("name"):
                self.remove(row)
                break

        self.save()

    @frappe.whitelist()
    def add_column(self, column):
        new_column = {
            "type": column.get("type"),
            "label": column.get("label"),
            "table": column.get("table"),
            "column": column.get("column"),
            "table_label": column.get("table_label"),
            "aggregation": column.get("aggregation"),
            "is_expression": column.get("is_expression"),
            "expression": dumps(column.get("expression"), indent=2),
            "format_option": dumps(column.get("format_option"), indent=2),
        }
        self.append("columns", new_column)
        self.save()

    @frappe.whitelist()
    def move_column(self, from_index, to_index):
        self.columns.insert(to_index, self.columns.pop(from_index))
        for row in self.columns:
            row.idx = self.columns.index(row) + 1
        self.save()

    @frappe.whitelist()
    def update_column(self, column):
        for row in self.columns:
            if row.get("name") == column.get("name"):
                row.type = column.get("type")
                row.label = column.get("label")
                row.table = column.get("table")
                row.column = column.get("column")
                row.order_by = column.get("order_by")
                row.aggregation = column.get("aggregation")
                row.table_label = column.get("table_label")
                row.aggregation_condition = column.get("aggregation_condition")
                format_option = column.get("format_option")
                if format_option:
                    # check if format option is an object
                    row.format_option = (
                        dumps(format_option, indent=2)
                        if isinstance(format_option, dict)
                        else format_option
                    )
                expression = column.get("expression")
                if expression:
                    # check if expression is an object
                    row.expression = (
                        dumps(expression, indent=2)
                        if isinstance(expression, dict)
                        else expression
                    )
                break

        self.save()

    @frappe.whitelist()
    def remove_column(self, column):
        for row in self.columns:
            if row.get("name") == column.get("name"):
                self.remove(row)
                break

        self.save()

    @frappe.whitelist()
    def update_filters(self, filters):
        sanitized_conditions = self.sanitize_conditions(filters.get("conditions"))
        filters["conditions"] = sanitized_conditions or []
        self.filters = dumps(filters, indent=2, default=cstr)
        self.save()

    def sanitize_conditions(self, conditions):
        if not conditions:
            return

        _conditions = deepcopy(conditions)

        for idx, condition in enumerate(_conditions):
            if "conditions" not in condition:
                # TODO: validate if condition is valid
                continue

            sanitized_conditions = self.sanitize_conditions(condition.get("conditions"))
            if sanitized_conditions:
                conditions[idx]["conditions"] = sanitized_conditions
            else:
                # remove the condition if it has zero conditions
                conditions.remove(condition)

        return conditions

    @frappe.whitelist()
    def apply_transform(self, type, data):
        self.transform_type = type
        self.transform_data = dumps(data, indent=2, default=cstr)
        if type == "Pivot":
            self.pivot(data)

        self.save()

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
    def fetch_tables(self):
        _tables = []
        if not self.tables or self.data_source == "Query Store":
            _tables = get_tables(self.data_source)

        else:
            tables = [d.table for d in self.tables]
            Table = frappe.qb.DocType("Insights Table")
            TableLink = frappe.qb.DocType("Insights Table Link")
            query = (
                frappe.qb.from_(Table)
                .from_(TableLink)
                .select(
                    TableLink.foreign_table.as_("table"),
                    TableLink.foreign_table_label.as_("label"),
                )
                .where((TableLink.parent == Table.name) & (Table.table.isin(tables)))
            )
            _tables = query.run(as_dict=True)
            # add all selected tables to the list too
            _tables = _tables + [
                {"table": d.table, "label": d.label} for d in self.tables
            ]

        if self.data_source == "Query Store":
            # remove the current query table from the table list
            # you should not be querying self
            _tables = [t for t in _tables if t.get("table") != self.name]

        return _tables

    @frappe.whitelist()
    def fetch_columns(self):
        if not self.tables:
            return []

        columns = []
        selected_tables = self.get_selected_tables()
        for table in selected_tables:
            table_doc = frappe.get_doc("Insights Table", {"table": table.get("table")})
            _columns = table_doc.get_columns()
            columns += [
                frappe._dict(
                    {
                        "table": table.get("table"),
                        "table_label": table.get("label"),
                        "column": c.get("column"),
                        "label": c.get("label"),
                        "type": c.get("type"),
                    }
                )
                for c in _columns
            ]
        return columns

    def get_selected_tables(self):
        join_tables = []
        for table in self.tables:
            if table.join:
                join = frappe.parse_json(table.join)
                join_tables.append(
                    frappe._dict(
                        {
                            "table": join.get("with").get("value"),
                            "label": join.get("with").get("label"),
                        }
                    )
                )

        return self.tables + join_tables

    @frappe.whitelist()
    def set_limit(self, limit):
        sanitized_limit = cint(limit)
        if not sanitized_limit or sanitized_limit < 0:
            frappe.throw("Limit must be a positive integer")
        self.limit = sanitized_limit
        self.save()

    @frappe.whitelist()
    def fetch_column_values(self, column, search_text=None) -> "list[str]":
        data_source = frappe.get_doc("Insights Data Source", self.data_source)
        return data_source.get_column_options(
            column.get("table"), column.get("column"), search_text
        )

    @frappe.whitelist()
    def fetch_join_options(self, table):
        doc = frappe.get_cached_doc(
            "Insights Table",
            {
                "table": table.get("table"),
                "data_source": self.data_source,
            },
        )

        return [
            {
                "primary_key": d.primary_key,
                "foreign_key": d.foreign_key,
                "table": d.foreign_table,
                "label": d.foreign_table_label,
            }
            for d in doc.get("table_links")
        ]

    @frappe.whitelist()
    def run(self):
        if self.data_source == "Query Store":
            tables = (t.table for t in self.tables)
            subqueries = frappe.db.get_all(
                "Insights Query", {"name": ["in", tables]}, pluck="name"
            )
            for subquery in subqueries:
                frappe.get_doc("Insights Query", subquery).run()
        self.build_and_execute()
        self.skip_before_save = True
        self.save()

    @frappe.whitelist()
    def reset(self):
        self.clear()
        self.skip_before_save = True
        self.save()

    @frappe.whitelist()
    def store(self):
        self.is_stored = 1
        self.save()
