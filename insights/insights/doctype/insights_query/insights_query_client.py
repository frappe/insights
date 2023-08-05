# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import cint

from insights.utils import InsightsChart


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
        return InsightsChart.get_name(query=self.name)

    @frappe.whitelist()
    def save_as_table(self):
        return self.update_insights_table(force=True)

    @frappe.whitelist()
    def delete_linked_table(self):
        return self.delete_insights_table()
