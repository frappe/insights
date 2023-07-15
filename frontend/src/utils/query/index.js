import { useQueryResource } from '@/query/useQueryResource'
import auth from '@/utils/auth'
import { useQueryColumns } from '@/utils/query/columns'
import { useQueryFilters } from '@/utils/query/filters'
import { useQueryResults } from '@/utils/query/results'
import { useQueryTables } from '@/utils/query/tables'
import { createToast } from '@/utils/toasts'
import { debounce } from 'frappe-ui'
import { computed } from 'vue'

export const API_METHODS = {
	run: 'run',
	store: 'store',
	convert: 'convert',
	setLimit: 'set_limit',
	duplicate: 'duplicate',
	reset: 'reset_and_save',
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

	addTransform: 'add_transform',
	resetTransforms: 'reset_transforms',
	getSourceSchema: 'get_source_schema',
	get_chart_name: 'get_chart_name',
}

export function useQuery(name) {
	const query = useQueryResource(name)
	query.beforeExecuteFns = []

	query.isOwner = computed(() => query.doc?.owner === auth.user.user_id)
	query.tables = useQueryTables(query)
	query.columns = useQueryColumns(query)
	query.filters = useQueryFilters(query)
	query.results = useQueryResults(query)

	query.sourceSchema = computed(() => query.getSourceSchema.data?.message)
	query.debouncedRun = debounce(query.run.submit, 500)
	query.beforeExecute = (fn) => {
		// since there are two query types,
		// and this one is used to execute the query for other
		query.beforeExecuteFns.push(fn)
	}
	query.execute = async () => {
		if (query.beforeExecuteFns.length) {
			await Promise.all(query.beforeExecuteFns.map((fn) => fn()))
			await query.get.fetch()
		}
		return query.debouncedRun(null, {
			onSuccess() {
				createToast({
					variant: 'success',
					title: 'Execution Successful',
				})
			},
			onError() {
				query.run.loading = false
				createToast({
					variant: 'error',
					title: 'Error while executing query',
					message: 'Please review the query and try again.',
				})
			},
		})
	}
	query.updateDoc = async (doc) => {
		await query.setValue.submit(doc)
	}

	return query
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
	now: {
		syntax: 'now()',
		description: 'Returns the current date and time',
		example: '`posting_date` = now()',
	},
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
	distinct_count: {
		syntax: 'distinct_count(column)',
		description: 'Returns the number of distinct values of the given column',
		example: 'distinct_count(`customer`)',
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
	descendants: {
		example: 'descendants("India", "tabTerritory", `territory)',
		description: 'Returns all descendants of the given value',
		syntax: 'descendants(value, doctype, fieldname)',
	},
	descendants_and_self: {
		example: 'descendants_and_self("India", "tabTerritory", `territory`)',
		description: 'Returns all descendants and self of the given value',
		syntax: 'descendants_and_self(value, doctype, fieldname)',
	},
	start_of: {
		example: 'start_of("Month", today())',
		description: 'Returns the start of the given unit eg. Month, Year, etc.',
		syntax: 'start_of(unit, date)',
	},
}
