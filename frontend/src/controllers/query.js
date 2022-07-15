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

	// visualization methods
	getVisualizations: 'get_visualizations',
	applyTransform: 'apply_transform',
}

export default class Query {
	NUMBER_FIELD_TYPES = ['Int', 'Decimal', 'Bigint', 'Float', 'Double']

	constructor(id) {
		this.id = id
		this.resource = getQueryResource(id)
		this._doc = computed(() => this.resource.doc)

		Object.keys(API_METHODS).forEach((key) => {
			if (!this[key]) {
				const whitelistedMethod = this.resource[key]
				this[key] = (...args) => {
					return {
						req: whitelistedMethod.submit(...args),
						data: computed(() => whitelistedMethod.data?.message),
						loading: computed(() => whitelistedMethod.loading),
					}
				}
				this[`${key}Data`] = computed(() => whitelistedMethod.data?.message)
			}
		})

		this.makeResult()
		this.visualizations = this.getVisualizations().data
	}

	get doc() {
		return this._doc.value
	}
	get status() {
		return this.doc.status
	}
	get dataSource() {
		return this.doc.data_source
	}
	get tables() {
		if (!this.doc) {
			return []
		}
		return this.doc.tables.map((table) => {
			return {
				...table,
				value: table.table,
				join: table.join ? safeJSONParse(table.join) : null,
			}
		})
	}
	get columns() {
		if (!this.doc) {
			return []
		}
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
		if (!this.doc) {
			return {}
		}
		return safeJSONParse(this.doc.filters)
	}

	makeResult() {
		this.result = computed(() => {
			if (!this.doc) {
				return []
			}
			return new QueryResult(this.doc, this.columns)
		})
	}

	getColumnValues(column) {
		const columnIdx = this.columns.findIndex((c) => c.column === column)
		if (columnIdx > -1) {
			return this.result.value.data.map((row) => row[columnIdx])
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
		this.formattedData = this.data
		this.formatCells()
	}

	formatCells() {
		this.formattedData = this.data.map((row) => {
			return row.map((cell, idx) => {
				const column = this.columns[idx]
				if (!column) {
					return cell
				}
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
		return cell
	}
}

function getQueryResource(name) {
	const doctype = 'Query'
	return createDocumentResource({ doctype, name, whitelistedMethods: API_METHODS })
}
