// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Query", {
	refresh(frm) {
		if (frm.doc.status == "Pending Execution") {
			frm.add_custom_button(__("Run"), () => {
				frm.call({
					method: "run",
					doc: frm.doc,
					callback: (r) => {
						frm.reload_doc();
					},
				});
			});
		}
	},
});
