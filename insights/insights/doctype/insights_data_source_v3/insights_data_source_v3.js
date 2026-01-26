// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Data Source v3", {
	refresh: function (frm) {
		frm.add_custom_button("Test Connection", function () {
			frm.call("test_connection", { raise_exception: true }).then((r) => {
				frappe.msgprint("Connection Successful");
			});
		});
	},
});
