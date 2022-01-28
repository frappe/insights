# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType, functions

AGGREGATIONS = {
	"Sum": functions.Sum,
}


class QueryField(Document):
	def before_insert(self):
		self.make_field()

	def autoname(self):
		self.name = self._field.get_sql(with_namespace=True, with_alias=True)

	def make_field(self):
		[doctype, fieldname] = self.field.split(".")
		self._field = DocType(doctype).field(fieldname)
		self.perform_aggregation()
		self.make_alias()

	def make_alias(self):
		if self.alias:
			self._field = self._field.as_(self.alias)

	def perform_aggregation(self):
		if self.aggregation:
			aggregation = AGGREGATIONS[self.aggregation]
			self._field = aggregation(self._field)
