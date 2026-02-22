// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Table Import Job", {
	refresh(frm) {
		frm.add_custom_button(__("Execute"), () => {
			frm.call("enqueue");
		});
	},
});
