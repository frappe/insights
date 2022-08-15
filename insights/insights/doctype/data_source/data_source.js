// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Data Source', {
	refresh: function (frm) {
		frm.add_custom_button('Test Connection', () => {
			frm.call('test_connection').then((res) => {
				frappe.show_alert({
					message: res.message
						? 'Connection Successful'
						: 'Connection Failed',
					indicator: res.message ? 'green' : 'red',
				})
			})
		})
		frm.add_custom_button('Import Tables', () => {
			frappe
				.run_serially([
					() => frappe.dom.freeze('Importing Tables...'),
					() => frm.call('import_tables'),
					() => frappe.dom.unfreeze(),
					() =>
						frappe.show_alert({
							message: 'Tables imported successfully',
							indicator: 'green',
						}),
				])
				.catch(() => frappe.dom.unfreeze())
		})
	},
})
