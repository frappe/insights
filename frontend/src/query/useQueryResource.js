import { safeJSONParse } from '@/utils'
import { createDocumentResource } from 'frappe-ui'

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
	get_chart_name: 'get_chart_name',

	run: 'run',
	get_chart_name: 'get_chart_name',
	convert_to_native: 'convert_to_native',
	convert_to_assisted: 'convert_to_assisted',
	get_tables_columns: 'get_tables_columns',
	save_as_table: 'save_as_table',
	delete_linked_table: 'delete_linked_table',
}

export function useQueryResource(name) {
	if (!name) return
	const resource = createDocumentResource({
		doctype: 'Insights Query',
		name: name,
		auto: false,
		whitelistedMethods: API_METHODS,
		transform(doc) {
			doc.columns = doc.columns.map((c) => {
				c.format_option = safeJSONParse(c.format_option, {})
				return c
			})
			doc.json = safeJSONParse(doc.json, defaultQueryJSON)
			doc.results = safeJSONParse(doc.results, [])
			resource.resultColumns = doc.results[0]
			return doc
		},
	})
	return resource
}

const defaultQueryJSON = {
	table: {},
	joins: [],
	filters: [],
	columns: [],
	calculations: [],
	measures: [],
	dimensions: [],
	orders: [],
	limit: null,
}
