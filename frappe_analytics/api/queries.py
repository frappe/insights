# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_docfield_list(doctype, txt, searchfield, start, page_len, filters):
	or_filters = [
		['fieldname', 'like', '%' + txt + '%'],
		['label', 'like', '%' + txt + '%'],
		['fieldtype', 'like', '%' + txt + '%']
	]

	docfields = frappe.get_all(
		doctype,
		fields=["name as value", "label", "fieldtype"],
		filters=filters,
		or_filters=or_filters,
		limit_start=start,
		limit_page_length=page_len,
		order_by="idx",
		as_list=1,
	)
	return docfields