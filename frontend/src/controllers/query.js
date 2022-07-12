import { computed } from 'vue'
import { createDocumentResource } from 'frappe-ui'
import { safeJSONParse } from '@/utils'

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
	NUMBER_FIELD_TYPES = ['Int', 'Decimal', 'Bigint', 'Float', 'Double']

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

		this.makeResult()
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
				join: table.join ? safeJSONParse(table.join) : null,
			}
		})
	}
	get columns() {
		return this.doc.columns.map((column) => {
			return {
				...column,
				value: column.column,
				format_option: column.format_option ? safeJSONParse(column.format_option) : null,
				aggregation_condition: column.aggregation_condition
					? safeJSONParse(column.aggregation_condition)
					: null,
			}
		})
	}
	get filters() {
		return safeJSONParse(this.doc.filters)
	}

	makeResult() {
		this.result = computed(() => new QueryResult(this.docRef.value, this.columns))
	}

	getColumnValues(column) {
		const columnIdx = this.columns.findIndex((c) => c.column === column)
		if (columnIdx > -1) {
			return this.result.map((row) => row[columnIdx])
		}
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

class QueryResult {
	MAX_ROWS = 1000
	NUMBER_FIELD_TYPES = ['Int', 'Decimal', 'Bigint', 'Float', 'Double']

	constructor(doc, columns) {
		this.doc = doc
		this.columns = columns
		this.data = safeJSONParse(doc.result, []).slice(0, this.MAX_ROWS)
		this.formatCells()
	}

	formatCells() {
		this.data = this.data.map((row) => {
			return row.map((cell, idx) => {
				const column = this.columns[idx]
				if (this.NUMBER_FIELD_TYPES.includes(column.type)) {
					cell = Number(cell).toLocaleString()
				}
				if (column.format_option) {
					cell = this.applyColumnFormatOption(column, cell)
				}
				return cell
			})
		})
	}

	applyColumnFormatOption(column, cell) {
		if (column.format_option.prefix) {
			return `${column.format_option.prefix} ${cell}`
		}
		if (column.format_option.suffix) {
			return `${cell} ${column.format_option.suffix}`
		}
	}
}

function getQueryResource(name) {
	const doctype = 'Query'
	return createDocumentResource({ doctype, name, whitelistedMethods: API_METHODS })
}
