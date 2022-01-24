# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class QueryField(Document):
	def before_insert(self):
		self.fetch_docfield_values()

	def before_save(self):
		self.fetch_docfield_values()

	def fetch_docfield_values(self):
		if self.field:
			# TODO: perf - get_value is called twice
			df = frappe.db.get_value('DocField', self.field, ['label', 'fieldname', 'fieldtype'], as_dict=True)
			self.label = df.label
			self.fieldname = df.fieldname
			self.type = df.fieldtype