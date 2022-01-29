# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import operator


class Operations:

	ARITHMETIC_OPERATIONS = {
		"+": operator.add,
		"-": operator.sub,
		"*": operator.mul,
		"/": operator.truediv,
	}
	COMPARE_OPERATIONS = {
		"=": operator.eq,
		"!=": operator.ne,
		"<": operator.lt,
		">": operator.gt,
		"<=": operator.le,
		">=": operator.ge,
	}
	COMPARE_FUNCTIONS = {
		"like": "like",
		"not like": "not_like",
		"in": "isin",
		"not in": "notin",
	}
	NULL_COMPARE_OPERATIONS = {"is set": "isnotnull", "is not set": "isnull"}
	RANGE_OPERATORS = {"between": "between"}

	@classmethod
	def get_operation(cls, operator):
		"""
		Returns a callable method which takes two arguments

		For eg.

		if `operator` = 'like'
		return `field.like(value)`
		where `field` and `value` are the two arguments

		"""
		if operator in cls.ARITHMETIC_OPERATIONS:
			return cls.ARITHMETIC_OPERATIONS[operator]

		if operator in cls.COMPARE_OPERATIONS:
			return cls.COMPARE_OPERATIONS[operator]

		if operator in cls.COMPARE_FUNCTIONS:
			function_name = cls.COMPARE_FUNCTIONS[operator]
			return lambda field, value: getattr(field, function_name)(value)

		if operator in cls.NULL_COMPARE_OPERATIONS:
			function_name = cls.NULL_COMPARE_OPERATIONS[operator]
			return lambda field, value: getattr(field, function_name)()

		if operator in cls.RANGE_OPERATORS:
			function_name = cls.RANGE_OPERATORS[operator]
			return lambda field, value: getattr(field, function_name)(
				value[0], value[1]
			)
