// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Data Source", {
	refresh: function (frm) {
		if (frm.name == "Query Store") {
			frm.set_read_only();
		}
	},
});
