export const FUNCTIONS = {
	// Comparison Operators
	in: {
		syntax: 'in(column_name, "value1", "value2", ...)',
		description: 'Checks if column contains any of the provided values.',
		example: 'in(`status`, "Closed", "Resolved")',
		returnType: 'boolean',
	},
	not_in: {
		syntax: 'not_in(column_name, "value1", "value2", ...)',
		description: 'Checks if column excludes the provided values.',
		example: 'not_in(`status`, "Closed", "Resolved")',
		returnType: 'boolean',
	},
	is_set: {
		syntax: 'is_set(column_name)',
		description: 'Checks if column has a value.',
		example: 'is_set(`status`)',
		returnType: 'boolean',
	},
	is_not_set: {
		syntax: 'is_not_set(column_name)',
		description: 'Checks if column lacks a value.',
		example: 'is_not_set(`status`)',
		returnType: 'boolean',
	},
	between: {
		syntax: 'between(column_name, "value1", "value2")',
		description: 'Checks if column value is between two values.',
		example: 'between(`age`, 10, 30)',
		returnType: 'boolean',
	},
	contains: {
		syntax: 'contains(column_name, "value")',
		description: 'Checks if column contains the specified value.',
		example: 'contains(`customer`, "John")',
		returnType: 'boolean',
	},
	not_contains: {
		syntax: 'not_contains(column_name, "value")',
		description: 'Checks if column excludes the specified value.',
		example: 'not_contains(`customer`, "John")',
		returnType: 'boolean',
	},
	ends_with: {
		syntax: 'ends_with(column_name, "value")',
		description: 'Checks if column ends with the specified value.',
		example: 'ends_with(`customer`, "Souza")',
		returnType: 'boolean',
	},
	starts_with: {
		syntax: 'starts_with(column_name, "value")',
		description: 'Checks if column starts with the specified value.',
		example: 'starts_with(`customer`, "John")',
		returnType: 'boolean',
	},

	// String Functions
	lower: {
		syntax: 'lower(string_column)',
		description: 'Converts string to lowercase.',
		example: 'lower(`category`)',
		returnType: 'string',
	},
	upper: {
		syntax: 'upper(string_column)',
		description: 'Converts string to uppercase.',
		example: 'upper(`category`)',
		returnType: 'string',
	},
	concat: {
		syntax: 'concat(column1, column2, ...)',
		description: 'Combines values from columns or strings.',
		example: 'concat(`first_name`, " ", `last_name`)',
		returnType: 'string',
	},
	replace: {
		syntax: 'replace(column_name, "search", "replace")',
		description: 'Replaces occurrences in the column.',
		example: 'replace(`category`, "_", "-")',
		returnType: 'string',
	},

	// Arithmetic Functions
	abs: {
		syntax: 'abs(number_column)',
		description: 'Returns absolute value of the column.',
		example: 'abs(`paid_amount`)',
		returnType: 'number',
	},
	sum: {
		syntax: 'sum(number_column)',
		description: 'Sums values of the column.',
		example: 'sum(`paid_amount`)',
		returnType: 'number',
	},
	min: {
		syntax: 'min(number_column)',
		description: 'Finds minimum value of the column.',
		example: 'min(`paid_amount`)',
		returnType: 'number',
	},
	max: {
		syntax: 'max(number_column)',
		description: 'Finds maximum value of the column.',
		example: 'max(`paid_amount`)',
		returnType: 'number',
	},
	avg: {
		syntax: 'avg(number_column)',
		description: 'Calculates average value of the column.',
		example: 'avg(`paid_amount`)',
		returnType: 'number',
	},
	round: {
		syntax: 'round(number_column)',
		description: 'Rounds the column value.',
		example: 'round(`paid_amount`)',
		returnType: 'number',
	},
	floor: {
		syntax: 'floor(number_column)',
		description: 'Rounds the column value down.',
		example: 'floor(`paid_amount`)',
		returnType: 'number',
	},
	ceil: {
		syntax: 'ceil(number_column)',
		description: 'Rounds the column value up.',
		example: 'ceil(`paid_amount`)',
		returnType: 'number',
	},

	// Date & Time Functions
	timespan: {
		syntax: 'timespan(column_name, "timespan")',
		description: 'Checks if column value is within the timespan.',
		example: 'timespan(`creation`, "Last 7 Days")',
		returnType: 'boolean',
	},
	now: {
		syntax: 'now()',
		description: 'Gets current date and time.',
		example: '`posting_date` = now()',
		returnType: 'datetime',
	},
	today: {
		syntax: 'today()',
		description: 'Gets current date.',
		example: '`posting_date` = today()',
		returnType: 'date',
	},
	start_of: {
		syntax: 'start_of(unit, date)',
		description: 'Finds start of the given unit (e.g., Month, Year).',
		example: 'start_of("Month", today())',
		returnType: 'date',
	},
	time_elapsed: {
		syntax: 'time_elapsed(unit, date1, date2)',
		description: 'Calculates time between two dates.',
		example: 'time_elapsed("day", `posting_date`, today())',
		returnType: 'number',
	},

	// Other Functions
	case: {
		syntax: 'case(condition1, "value1", ..., "default_value")',
		description: 'Returns matched condition value or default.',
		example: 'case(`amount` > 0, "Unpaid", `amount` < 0, "Return", "Paid")',
		returnType: 'any',
	},
	count: {
		syntax: 'count(column_name)',
		description: 'Counts rows based on column.',
		example: 'count(`ID`)',
		returnType: 'number',
	},
	coalesce: {
		syntax: 'coalesce(column1, column2, ...)',
		description: 'Returns first non-null value from columns.',
		example: 'coalesce(`first_name`, `last_name`)',
		returnType: 'any',
	},
	if_null: {
		syntax: 'if_null(column_name, "default_value")',
		description: 'Provides default if column is null.',
		example: 'if_null(`category`, "No Category")',
		returnType: 'any',
	},
	distinct: {
		syntax: 'distinct(column_name)',
		description: 'Lists distinct values of the column.',
		example: 'distinct(`customer`)',
		returnType: 'any',
	},
	distinct_count: {
		syntax: 'distinct_count(column_name)',
		description: 'Counts distinct values of the column.',
		example: 'distinct_count(`customer`)',
		returnType: 'number',
	},
	count_if: {
		syntax: 'count_if(condition)',
		description: 'Counts rows that satisfy the condition.',
		example: 'count_if(`amount` > 0)',
		returnType: 'number',
	},
	sum_if: {
		syntax: 'sum_if(condition, column_name)',
		description: 'Sums values of the column that satisfy the condition.',
		example: 'sum_if(`customer` = "John", `grand_total`)',
		returnType: 'number',
	},
	descendants: {
		syntax: 'descendants("value", "doctype", "fieldname")',
		description: 'Lists all descendants of the given value.',
		example: 'descendants("India", "tabTerritory", `territory`)',
		returnType: 'boolean',
	},
	descendants_and_self: {
		syntax: 'descendants_and_self("value", "doctype", "fieldname")',
		description: 'Lists all descendants and self of the given value.',
		example: 'descendants_and_self("India", "tabTerritory", `territory`)',
		returnType: 'boolean',
	},
	sql: {
		syntax: 'sql("query")',
		description: 'Write raw SQL queries.',
		example: 'sql("MONTH(invoice.posting_date)")',
		returnType: 'any',
	},
}
