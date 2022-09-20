import { computed } from 'vue'
import { createDocumentResource, debounce } from 'frappe-ui'
import { useQueryTables } from '@/utils/query/tables'
import { useQueryColumns } from '@/utils/query/columns'
import { useQueryFilters } from '@/utils/query/filters'
import { useQueryResults } from '@/utils/query/results'

const API_METHODS = {
	run: 'run',
	reset: 'reset',
	setLimit: 'set_limit',
	duplicate: 'duplicate',
	fetchTables: 'fetch_tables',
	fetchColumns: 'fetch_columns',
	fetchColumnValues: 'fetch_column_values',

	// table methods
	addTable: 'add_table',
	removeTable: 'remove_table',
	updateTable: 'update_table',
	fetchJoinOptions: 'fetch_join_options',

	// column methods
	addColumn: 'add_column',
	moveColumn: 'move_column',
	updateColumn: 'update_column',
	removeColumn: 'remove_column',

	// filter methods
	updateFilters: 'update_filters',

	// visualization methods
	getVisualizations: 'get_visualizations',
	applyTransform: 'apply_transform',
}

export function useQuery(name) {
	const query = getQueryResource(name)

	query.tables = useQueryTables(query)
	query.columns = useQueryColumns(query)
	query.filters = useQueryFilters(query)
	query.results = useQueryResults(query)

	query.getVisualizations.submit()
	query.visualizations = computed(() => query.getVisualizations.data?.message)
	query.debouncedRun = debounce(query.run.submit, 500)

	return query
}

function getQueryResource(name) {
	const doctype = 'Insights Query'
	return createDocumentResource({
		doctype,
		name,
		whitelistedMethods: API_METHODS,
	})
}

export const FUNCTIONS = {
	//
	// Operators
	//
	in: {
		syntax: 'in(column, value1, value2, ...)',
		description: 'Check if a column contains one of the given values',
		example: 'in(status, "Closed", "Resolved")',
	},
	not_in: {
		syntax: 'not_in(column, value1, value2, ...)',
		description: 'Check if a column does not contain one of the given values',
		example: 'not_in(`status`, "Closed", "Resolved")',
	},
	is_set: {
		syntax: 'is_set(column)',
		description: 'Check if a column is set',
		example: 'is_set(`status`)',
	},
	is_not_set: {
		syntax: 'is_not_set(column)',
		description: 'Check if a column is not set',
		example: 'is_not_set(`status`)',
	},
	between: {
		syntax: 'between(column, value1, value2)',
		description: 'Check if a column is between two values',
		example: 'between(`age`, 10, 30)',
	},
	timespan: {
		syntax: 'timespan(column, value)',
		description: 'Check if a column is within the given timespan',
		example: 'timespan(`creation`, "Last 7 Days")',
	},
	contains: {
		syntax: 'contains(column, value)',
		description: 'Check if a column contains the given value',
		example: 'contains(`customer`, "John")',
	},
	not_contains: {
		syntax: 'not_contains(column, value)',
		description: 'Check if a column does not contain the given value',
		example: 'not_contains(`customer`, "John")',
	},
	ends_with: {
		syntax: 'ends_with(column, value)',
		description: 'Check if a column ends with the given value',
		example: 'ends_with(`customer`, "Souza")',
	},
	starts_with: {
		syntax: 'starts_with(column, value)',
		description: 'Check if a column starts with the given value',
		example: 'starts_with(`customer`, "John")',
	},
	//
	// Others
	//
	abs: {
		syntax: 'abs(number_column)',
		description: 'Returns the absolute value of the given number column',
		example: 'abs(`paid_amount`)',
	},
	sum: {
		syntax: 'sum(number_column)',
		description: 'Returns the sum of the given number column',
		example: 'sum(`paid_amount`)',
	},
	min: {
		syntax: 'min(number_column)',
		description: 'Returns the minimum value of the given number column',
		example: 'min(`paid_amount`)',
	},
	max: {
		syntax: 'max(number_column)',
		description: 'Returns the maximum value of the given number column',
		example: 'max(`paid_amount`)',
	},
	avg: {
		syntax: 'avg(number_column)',
		description: 'Returns the average value of the given number column',
		example: 'avg(`paid_amount`)',
	},
	ceil: {
		syntax: 'ceil(number_column)',
		description: 'Returns the ceiling of the given number column',
		example: 'ceil(`paid_amount`)',
	},
	floor: {
		syntax: 'floor(number_column)',
		description: 'Returns the floor of the given number column',
		example: 'floor(`paid_amount`)',
	},
	lower: {
		syntax: 'lower(string_column)',
		description: 'Returns the lowercase of the given string column',
		example: 'lower(`category`)',
	},
	upper: {
		syntax: 'upper(string_column)',
		description: 'Returns the uppercase of the given string column',
		example: 'upper(`category`)',
	},
	round: {
		syntax: 'round(number_column)',
		description: 'Returns the rounded value of the given number column',
		example: 'round(`paid_amount`)',
	},
	count: {
		syntax: 'count(column)',
		description: 'Count the number of rows',
		example: 'count(`ID`)',
	},
	concat: {
		syntax: 'concat(column1, column2, ...)',
		description: 'Concatenates multiple columns or strings',
		example: 'concat(`first_name`, " ", `last_name`)',
	},
	coalesce: {
		syntax: 'coalesce(column1, column2, ...)',
		description: 'Returns the first non-null value of the given columns',
		example: 'coalesce(`first_name`, `last_name`)',
	},
	if_null: {
		syntax: 'if_null(column, default_value)',
		description: 'Returns default_value if column is null',
		example: 'if_null(`category`, "No Category")',
	},
	replace: {
		syntax: 'replace(column, search, replace)',
		description: 'Replaces all occurrences of search with replace in column',
		example: 'replace(`category`, "_", "-")',
	},
	now: 'now',
	today: {
		syntax: 'today()',
		description: 'Returns the current date',
		example: '`posting_date` = today()',
	},
	case: {
		syntax: 'case(condition1, value1, ..., default_value)',
		description:
			'Returns value1 if condition1 is true, and same for more conditions else default_value',
		example:
			'case(`outstanding_amount` > 0, "Unpaid", `outstanding_amount` < 0, "Return", "Paid")',
	},
	count_if: {
		syntax: 'count_if(condition)',
		description: 'Counts the number of rows that satisfy the condition',
		example: 'count_if(`outstanding_amount` > 0)',
	},
	distinct: {
		syntax: 'distinct(column)',
		description: 'Returns distinct values of the given column',
		example: 'distinct(`customer`)',
	},
	sum_if: {
		syntax: 'sum_if(condition, column)',
		description: 'Returns the sum of the values of the given column that satisfy the condition',
		example: 'sum_if(`customer` = "John", `grand_total`)',
	},
	time_elapsed: {
		syntax: 'time_elapsed(unit, date1, date2)',
		description: 'Returns the time elapsed between two dates',
		example: 'time_elapsed("day", `posting_date`, today())',
	},
}
