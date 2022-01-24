# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Query(Document):
	def before_save(self):
		for filter in self.filters:
			filter.second_operand = (
				filter.link_value
				if filter.value_is_a_query_field
				else filter.data_value
			)
