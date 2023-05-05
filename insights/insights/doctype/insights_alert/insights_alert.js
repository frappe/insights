// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Alert", {
	refresh: function (frm) {
		if (frm.doc.disabled) return;
		frm.add_custom_button(__("Send Alert"), function () {
			frappe.dom.freeze(__("Sending Alert..."));
			frm.call("send_alert")
				.then(() => {
					frappe.dom.unfreeze();
					frappe.show_alert({
						message: __("Alert sent"),
						indicator: "green",
					});
				})
				.catch(() => {
					frappe.dom.unfreeze();
				});
		});
	},
});
