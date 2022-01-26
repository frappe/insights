// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Query", {
	setup(frm) {
		const show_doctype_and_field_options_on = [
			["field_1", "columns"],
			["field_2", "columns"],
			["first_operand", "filters"],
			["link_value", "filters"],
			["first_operand", "join_conditions"],
			["link_value", "join_conditions"],
			["sort_by"]
		]
		show_doctype_and_field_options_on.map(field => {
			const args = [...field, () => {
				return {
					query: "frappe_analytics.api.queries.get_doctype_and_field_options",
				};
			}];
			frm.set_query(...args);
		})
	}
});
