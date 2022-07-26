import { computed } from 'vue'
import { createDocumentResource } from 'frappe-ui'
import { useQueryTables } from '@/utils/query/tables'
import { useQueryColumns } from '@/utils/query/columns'
import { useQueryFilters } from '@/utils/query/filters'
import { useQueryResults } from '@/utils/query/results'

const API_METHODS = {
	run: 'run',
	reset: 'reset',
	setLimit: 'set_limit',
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

	return query
}

function getQueryResource(name) {
	const doctype = 'Query'
	return createDocumentResource({
		doctype,
		name,
		whitelistedMethods: API_METHODS,
	})
}

export const FUNCTIONS = {
	abs: 'abs',
	in: 'in',
	not_in: 'not in',
	case: 'case',
	floor: 'floor',
	lower: 'lower',
	upper: 'upper',
	concat: 'concat',
	is_set: 'is set',
	is_not_set: 'is not set',
	if_null: 'if null',
	coalesce: 'coalesce',
	between: 'between',
	timespan: 'timespan',
	contains: 'contains',
	ends_with: 'ends with',
	starts_with: 'starts with',
	ceil: 'ceil',
	round: 'round',
	replace: 'replace',
}
