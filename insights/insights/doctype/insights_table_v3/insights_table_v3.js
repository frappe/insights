// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Table v3", {
	refresh: function (frm) {
		if (frm.doc.stored) {
			frm.add_custom_button(__("Import to Warehouse"), function () {
				frm.call("import_to_warehouse").then(() => {
					frappe.msgprint(__("Import job has been queued"));
				});
			});
		}
	},
});
