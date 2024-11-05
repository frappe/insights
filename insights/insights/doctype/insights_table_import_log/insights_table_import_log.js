// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Table Import Log", {
	refresh(frm) {
		if (frm.doc.status == "In Progress") {
			frm.add_custom_button(__("Mark as Failed"), function () {
				frm.call("mark_as_failed").then(() => {
					frm.reload_doc();
				});
			});
		}
	},
});
