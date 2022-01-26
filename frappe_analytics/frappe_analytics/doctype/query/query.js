// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Query", {
	setup(frm) {
		frm.set_query("field_1", "columns", () => {
			return {
				query: "frappe_analytics.api.queries.get_doctype_and_field_options",
			};
		});
		frm.set_query("field_2", "columns", () => {
			return {
				query: "frappe_analytics.api.queries.get_doctype_and_field_options",
			};
		});
		frm.set_query("first_operand", "filters", () => {
			return {
				query: "frappe_analytics.api.queries.get_doctype_and_field_options",
			};
		});
		frm.set_query("link_value", "filters", () => {
			return {
				query: "frappe_analytics.api.queries.get_doctype_and_field_options",
			};
		});
		frm.set_query("sort_by", () => {
			return {
				query: "frappe_analytics.api.queries.get_doctype_and_field_options",
			};
		});
	},
});
