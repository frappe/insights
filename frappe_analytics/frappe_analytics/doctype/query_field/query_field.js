// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Query Field', {
	setup(frm) {
		frm.set_query("field", () => {
			return {
				query: "frappe_analytics.api.queries.get_doctype_and_field_options",
			};
		});
	}
});
