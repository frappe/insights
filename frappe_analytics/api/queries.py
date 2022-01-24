# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


@frappe.whitelist()
def get_doctype_and_field_options(txt):
	if not txt or "." not in txt:
		filters = {"issingle": 0}
		if txt:
			filters.update({"name": ["like", f"%{txt}%"]})

		return frappe.get_all("DocType", filters, pluck="name", limit=20)

	if "." in txt:
		doctype = txt.split(".")[0].title()
		meta = frappe.get_meta(doctype)
		valid_columns = meta.get_valid_columns()
		return [f"{meta.name}.{d}" for d in valid_columns]
