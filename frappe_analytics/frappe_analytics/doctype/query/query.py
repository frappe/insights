# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import operator
from json import dumps
from sqlparse import format as format_sql

import frappe
from frappe import _, throw
from frappe.utils import cstr
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
from frappe.query_builder import Field, Criterion, DocType, functions, JoinType


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
	"Sum": functions.Sum,
}


# TODO: Make Enum of Aggregations


class Query(Document):
	def validate(self):
		# TODO: validate if a column is an expression and aggregation is "group by"
		pass

	def before_save(self):
		self.execute()
		self.sql = format_sql(
			str(self._query), keyword_case="upper", reindent_aligned=True
		)
		self.result = dumps(self._result, default=cstr)

	def process(self):
		self._tables = []
		self.process_columns()
		self.process_filters()
		self.process_joins()
		self.process_sorting()
		self.process_limits()
		self.process_tables()

	def execute(self):
		self.process()
		query = (
			self.from_tables.from_(self.table)
			.join(self._join_table, self._join_type)
			.on(Criterion.all(self._join_conditions))
			.select(*self._columns)
			.where(Criterion.all(self._filters))
			.limit(self._limit)
		)

		if self._group_by_columns:
			query = query.groupby(*self._group_by_columns).having(
				Criterion.all(self._having_conditions)
			)

		if self._sort_by:
			query = query.orderby(self._sort_by)

		self._query = query
		self._result = query.run()
		self._result = list(self._result)
		self.format_result()

	def process_columns(self):
		self._columns = []
		self._group_by_columns = []

		for column in self.columns:
			field = self.convert_to_field(column.field_1)

			if column.aggregation_1:
				if column.aggregation_1 != "Group By":
					aggregation = OPERATOR_MAP[column.aggregation_1]
					field = aggregation(field)
				else:
					self._group_by_columns.append(field)

			if column.alias_1:
				field = field.as_(column.alias_1)

			self._columns.append(field)

	def process_filters(self):
		self._filters = []
		self._having_conditions = []
		Query.set_second_operand(self.filters)
		for filter in self.filters:
			expression = self.convert_to_expression(filter)
			if filter.aggregation_1 or filter.aggregation_2:
				self._having_conditions.append(expression)
			else:
				self._filters.append(expression)

	def convert_to_expression(self, condition):
		operand_1 = self.convert_to_field(condition.first_operand)

		if condition.aggregation_1:
			aggregation = OPERATOR_MAP[condition.aggregation_1]
			operand_1 = aggregation(operand_1)

		operand_2 = (
			self.convert_to_field(condition.second_operand)
			if condition.value_is_a_query_field
			else condition.second_operand
		)

		if condition.value_is_a_query_field and condition.aggregation_2:
			aggregation = OPERATOR_MAP[condition.aggregation_2]
			operand_2 = aggregation(operand_2)

		operation = OPERATOR_MAP[condition.operator]
		return operation(operand_1, operand_2)

	@staticmethod
	def set_second_operand(filters):
		for filter in filters:
			filter.second_operand = (
				filter.link_value
				if filter.value_is_a_query_field
				else filter.data_value
			)

	def process_joins(self):
		if not self.join_table:
			return

		if not self.join_type:
			throw(_("Please select a join type"))

		self._join_table = DocType(self.join_table)

		join_type = self.join_type.split(" ")[0].lower()
		self._join_type = JoinType[join_type]

		Query.set_second_operand(self.join_conditions)
		self._join_conditions = []
		for condition in self.join_conditions:
			expression = self.convert_to_expression(condition)
			self._join_conditions.append(expression)

	def process_sorting(self):
		self._sort_by = self.convert_to_field(self.sort_by) if self.sort_by else None

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
		column = table.field(fieldname)
		self.add_to_tables_list(doctype, table)
		return column

	def add_to_tables_list(self, doctype, table):
		if (
			doctype
			and doctype not in [self.table, self.join_table]
			and table not in self._tables
		):
			self._tables.append(table)

	def format_result(self):
		column_names = [d.alias or d.name for d in self._columns]
		self._result.insert(0, column_names)
