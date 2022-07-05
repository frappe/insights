import { computed } from 'vue'
import { createDocumentResource } from 'frappe-ui'

const API_METHODS = {
	run: 'run',
	reset: 'reset',
	setLimit: 'set_limit',
	fetchTables: 'fetch_tables',
	fetchColumns: 'fetch_columns',
	fetchColumnValues: 'fetch_column_values',
	fetchOperatorList: 'fetch_operator_list',

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

	// transform methods
	applyTransform: 'apply_transform',
}

export default class Query {
	constructor(id) {
		this.id = id
		this.resource = getQueryResource(id)
		this.docRef = computed(() => this.resource.doc)

		Object.keys(API_METHODS).forEach((key) => {
			if (!this[key]) {
				this[key] = (...args) => this.resource[key].submit(...args)
				this[`${key}Data`] = computed(() => this.resource[key].data?.message)
			}
		})
	}

	get doc() {
		return this.docRef.value
	}
	get status() {
		return this.doc.status
	}
	get dataSource() {
		return this.doc.data_source
	}
	get tables() {
		return this.doc.tables.map((table) => {
			return {
				...table,
				value: table.table,
				join: table.join ? JSON.parse(table.join) : null,
			}
		})
	}
	get columns() {
		return this.doc.columns.map((column) => {
			return {
				...column,
				value: column.column,
				aggregation_condition: column.aggregation_condition
					? JSON.parse(column.aggregation_condition)
					: null,
			}
		})
	}
	get filters() {
		return JSON.parse(this.doc.filters)
	}
	get result() {
		return JSON.parse(this.doc.result || '[]')
	}

	setValue(key, value) {
		return this.resource.setValue.submit({ [key]: value })
	}

	setLimit({ limit }) {
		if (parseInt(limit, 10) > 0) {
			return this.resource.setLimit.submit({ limit })
		}
	}

	reload() {
		return this.resource.reload.submit()
	}

	delete() {
		return this.resource.delete.submit()
	}
}

function getQueryResource(name) {
	const doctype = 'Query'
	return createDocumentResource({ doctype, name, whitelistedMethods: API_METHODS })
}
