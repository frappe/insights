// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Query Field', {
	setup(frm) {
		const no_value_fields = [
			'Section Break',
			'Column Break',
			'Tab Break',
			'HTML',
			'Table',
			'Table MultiSelect',
			'Button',
			'Image',
			'Fold',
			'Heading'
		]
		frm.set_query('field', () => {
			return {
				query: 'frappe_analytics.api.queries.get_docfield_list',
				filters: {
					parent: frm.doc.table,
					fieldtype: ['not in', no_value_fields]
				}
			};
		});
	}
});
