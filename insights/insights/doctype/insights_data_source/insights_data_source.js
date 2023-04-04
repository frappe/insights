// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Data Source", {
	refresh: function (frm) {
		if (frm.doc.status === "Active") {
			frm.add_custom_button(__("Sync Tables"), async function () {
				frappe.dom.freeze(__("Syncing Tables"));
				await frm.call("sync_tables");
				frappe.dom.unfreeze();
			});
		}
	},
});
