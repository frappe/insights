// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Data Source", {
	refresh: function (frm) {
		frm.add_custom_button(__("Import Table"), function () {
			frm.call("get_db_tables").then(function (r) {
				if (r.message) {
					const dialog = new frappe.ui.Dialog({
						title: __("Import Table"),
						fields: [
							{
								fieldname: "table",
								label: __("Table"),
								fieldtype: "Autocomplete",
								options: r.message,
								reqd: 1,
							},
						],
					});

					dialog.set_primary_action(__("Import"), function () {
						const table = dialog.get_value("table");
						frm.call("import_table", { table_name: table }).then(
							function (r) {
								frappe.msgprint(
									__("Table imported successfully")
								);
								frm.reload_doc();
							}
						);
						dialog.hide();
					});

					dialog.show();
				}
			});
		});

		frm.add_custom_button(__("Update Table List"), function () {
			frm.call("update_table_list").then(function (r) {
				if (r.message) {
					frm.reload_doc();
					frappe.msgprint(__("Table list updated successfully"));
				}
			});
		});
	},
});
