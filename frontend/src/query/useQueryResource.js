import { safeJSONParse } from '@/utils'
import { createDocumentResource } from 'frappe-ui'

export const API_METHODS = {
	run: 'run',
	store: 'store',
	unstore: 'unstore',
	convert: 'convert',
	setLimit: 'set_limit',
	set_status: 'set_status',
	duplicate: 'duplicate',
	reset: 'reset_and_save',
	fetchTables: 'fetch_tables',
	fetchColumns: 'fetch_columns',
	fetchColumnValues: 'fetch_column_values',
	fetch_related_tables: 'fetch_related_tables',

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

	run: 'run',
	convert_to_native: 'convert_to_native',
	convert_to_assisted: 'convert_to_assisted',
	get_tables_columns: 'get_tables_columns',
	save_as_table: 'save_as_table',
	delete_linked_table: 'delete_linked_table',
	switch_query_type: 'switch_query_type',
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
			doc.transforms = doc.transforms.map((t) => {
				t.options = safeJSONParse(t.options, {})
				return t
			})
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
