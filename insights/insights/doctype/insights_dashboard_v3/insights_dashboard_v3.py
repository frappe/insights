# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class InsightsDashboardv3(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        is_public: DF.Check
        items: DF.JSON | None
        linked_charts: DF.JSON | None
        old_name: DF.Data | None
        preview_image: DF.Data | None
        share_link: DF.Data | None
        title: DF.Data | None
        workbook: DF.Link | None
    # end: auto-generated types

    def get_valid_dict(self, *args, **kwargs):
        if isinstance(self.items, list):
            self.items = frappe.as_json(self.items)
        if isinstance(self.linked_charts, list):
            self.linked_charts = frappe.as_json(self.linked_charts)
        return super().get_valid_dict(*args, **kwargs)

    def before_save(self):
        self.set_linked_charts()

    def set_linked_charts(self):
        linked_charts = []
        for item in frappe.parse_json(self.items):
            if item["type"] == "chart":
                linked_charts.append(item["chart"])
        self.linked_charts = linked_charts

    @frappe.whitelist(allow_guest=True)
    def get_distinct_column_values(self, query, column_name, search_term=None):
        is_guest = frappe.session.user == "Guest"
        if not is_guest and not self.is_public:
            raise frappe.PermissionError

        self.check_linked_filters(query, column_name)

        doc = frappe.get_cached_doc("Insights Query v3", query)
        return doc.get_distinct_column_values(column_name, search_term=search_term)

    def check_linked_filters(self, query, column_name):
        items = frappe.parse_json(self.items)
        filters = [item for item in items if item["type"] == "filter"]
        for f in filters:
            # check if there is a filter which has "link": { 'chart': "`<query>`.`<column>`" }
            linked_columns = f.get("links", {}).values()
            pattern = "^`([^`]+)`\\.`([^`]+)`$"
            for linked_column in linked_columns:
                match = re.match(pattern, linked_column)
                if (
                    match
                    and match.groups()[0] == query
                    and match.groups()[1] == column_name
                ):
                    return True

        raise frappe.PermissionError
