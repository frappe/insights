# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import operator
from json import dumps

import frappe
from functools import reduce
from frappe.database.query import (
	func_in,
	func_not_in,
	like,
	not_like,
	func_regex,
	func_between,
)
from frappe.model.document import Document
from frappe.query_builder import Field, Criterion, DocType


OPERATOR_MAP = {
	"+": operator.add,
	"*": operator.mul,
	"/": operator.truediv,
	"=": operator.eq,
	"-": operator.sub,
	"!=": operator.ne,
	"<": operator.lt,
	">": operator.gt,
	"<=": operator.le,
	">=": operator.ge,
	"in": func_in,
	"not in": func_not_in,
	"like": like,
	"not like": not_like,
	"regex": func_regex,
	"between": func_between,
}


class Query(Document):
	def before_save(self):
		self.process()
		self.execute()
		self.result = dumps(self._result)

	def process(self):
		self._tables = []
		self.process_columns()
		self.process_filters()
		self.process_sorting()
		self.process_limits()
		self.process_tables()

	@frappe.whitelist()
	def execute(self):
		self.process()
		query = (
			self.from_tables.select(*self._columns)
			.where(Criterion.all(self._filters))
			.orderby(self._sort_by)
			.limit(self._limit)
		)

		self._result = query.run()
		self._result = list(self._result)
		column_names = [d.name for d in self._columns]
		self._result.insert(0, column_names)

	def process_columns(self):
		self._columns = []

		for column in self.columns:
			field = self.convert_to_field(column.primary_field)
			self._columns.append(field)

	def process_filters(self):
		self._filters = []
		self.set_second_operand()
		for filter in self.filters:
			operand_1 = self.convert_to_field(filter.first_operand)
			operand_2 = (
				self.convert_to_field(filter.second_operand)
				if filter.value_is_a_query_field
				else filter.second_operand
			)
			operation = OPERATOR_MAP[filter.operator]
			expression = operation(operand_1, operand_2)
			self._filters.append(expression)

	def set_second_operand(self):
		for filter in self.filters:
			filter.second_operand = (
				filter.link_value
				if filter.value_is_a_query_field
				else filter.data_value
			)

	def process_sorting(self):
		if self.sort_by:
			self._sort_by = self.convert_to_field(self.sort_by)

	def process_limits(self):
		self._limit: int = self.limit or 10

	def process_tables(self):
		self.from_tables = reduce(
			lambda qb, table: qb.from_(table),
			self._tables,
			frappe.qb,
		)

	def convert_to_field(self, field: str) -> Field:
		[doctype, fieldname] = field.split(".")
		table = DocType(doctype)
		if table not in self._tables:
			self._tables.append(table)
		column = table.field(fieldname)
		return column
