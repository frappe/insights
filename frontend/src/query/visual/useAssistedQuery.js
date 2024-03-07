import { areDeeplyEqual, makeColumnOption, run_doc_method } from '@/utils'
import { createToast } from '@/utils/toasts'
import { watchDebounced } from '@vueuse/core'
import { debounce } from 'frappe-ui'
import { computed, onMounted, reactive } from 'vue'
import { NEW_COLUMN, NEW_FILTER, NEW_JOIN } from './constants'
import {
	ERROR_CANNOT_ADD_SELF_AS_TABLE,
	ERROR_UNABLE_TO_RESET_MAIN_TABLE,
	WARN_UNABLE_TO_INFER_JOIN,
} from './messages'
import {
	inferJoinForTable,
	inferJoinsFromColumns,
	isTableAlreadyAdded,
	makeNewColumn,
	sanitizeQueryJSON,
} from './utils'

export default function useAssistedQuery(query) {
	const state = reactive({
		data_source: computed(() => query.doc.data_source),
		table: {},
		joins: [],
		columns: [],
		filters: [],
		calculations: [],
		dimensions: [],
		measures: [],
		orders: [],
		limit: 100,
		transforms: computed(() => [...query.doc.transforms]),
		joinAssistEnabled: true,
		columnOptions: [],
		groupedColumnOptions: [],
		setDataSource,
		addTable,
		resetMainTable,
		removeJoinAt,
		updateJoinAt,
		addColumns,
		removeColumnAt,
		updateColumnAt,
		moveColumn,
		addFilter,
		removeFilterAt,
		updateFilterAt,
		setOrderBy,
		setLimit,
		addTransform,
		removeTransformAt,
		updateTransformAt,
		fetchColumnOptions: debounce(fetchColumnOptions, 500),
	})

	onMounted(() => {
		const queryJSON = sanitizeQueryJSON(query.doc.json)
		state.table = queryJSON.table
		state.joins = queryJSON.joins
		state.columns = queryJSON.columns
		state.filters = queryJSON.filters
		state.calculations = queryJSON.calculations
		state.dimensions = queryJSON.dimensions
		state.measures = queryJSON.measures
		state.orders = queryJSON.orders
		state.limit = queryJSON.limit
	})

	watchDebounced(
		() => {
			return {
				table: state.table,
				joins: state.joins,
				columns: state.columns,
				filters: state.filters,
				calculations: state.calculations,
				dimensions: state.dimensions,
				measures: state.measures,
				orders: state.orders,
				limit: state.limit,
			}
		},
		(newQuery, oldQuery) => {
			const tablesChanged = hasTablesChanged(newQuery, oldQuery)
			query.updateQuery(newQuery).then(({ query_updated }) => {
				query_updated && tablesChanged && fetchColumnOptions()
			})
		},
		{ deep: true, debounce: 500 }
	)

	async function fetchColumnOptions(search_txt = '') {
		if (!state.data_source) return
		const search_txt_lower = search_txt.toLowerCase()
		const res = await run_doc_method('fetch_related_tables_columns', query.doc, {
			search_txt: search_txt_lower,
		})
		state.columnOptions = res.message.map(makeColumnOption)
		state.groupedColumnOptions = makeGroupedColumnOptions(res.message)
	}

	async function setDataSource(dataSource) {
		if (!dataSource || query.doc.data_source) return
		return query.changeDataSource(dataSource)
	}

	async function addTable(newTable) {
		if (!newTable?.table) return
		if (newTable.table === query.doc.name) {
			return createToast(ERROR_CANNOT_ADD_SELF_AS_TABLE())
		}
		const mainTable = state.table
		if (!mainTable?.table) {
			state.table = { table: newTable.table, label: newTable.label }
			return
		}
		if (isTableAlreadyAdded(state, newTable)) return
		const join = await inferJoinForTable(newTable, state)
		if (join) {
			return state.joins.push(join)
		}
		createToast(WARN_UNABLE_TO_INFER_JOIN(mainTable.label, newTable.label))
		state.joins.push({
			...NEW_JOIN,
			left_table: { table: mainTable.table, label: mainTable.label },
			right_table: { table: newTable.table, label: newTable.label },
		})
	}

	function resetMainTable() {
		if (state.joins.length || state.columns.length) {
			createToast(ERROR_UNABLE_TO_RESET_MAIN_TABLE())
			return
		}
		state.table = {}
	}

	function removeJoinAt(joinIdx) {
		state.joins.splice(joinIdx, 1)
	}

	function updateJoinAt(joinIdx, newJoin) {
		state.joins.splice(joinIdx, 1, newJoin)
	}

	function addColumns(addedColumns) {
		const newColumns = addedColumns.map(makeNewColumn)
		state.columns.push(...newColumns)
		state.joinAssistEnabled && inferJoins()
	}

	function removeColumnAt(removedColumnIdx) {
		state.columns.splice(removedColumnIdx, 1)
	}

	function updateColumnAt(updatedColumnIdx, newColumn) {
		state.columns.splice(updatedColumnIdx, 1, newColumn)
		state.joinAssistEnabled && inferJoins()
	}

	function moveColumn(oldIndex, newIndex) {
		state.columns.splice(newIndex, 0, state.columns.splice(oldIndex, 1)[0])
	}

	function addFilter() {
		state.filters.push({ ...NEW_FILTER })
	}
	function removeFilterAt(removedFilterIdx) {
		state.filters.splice(removedFilterIdx, 1)
	}
	function updateFilterAt(updatedFilterIdx, newFilter) {
		state.filters.splice(updatedFilterIdx, 1, newFilter)
		state.joinAssistEnabled && inferJoins()
	}

	function setOrderBy(column, order) {
		state.columns.some((c) => {
			if (c.label === column) {
				c.order = order
				return true
			}
		})
	}

	function setLimit(limit) {
		if (limit === state.limit) return
		state.limit = limit
	}

	function addTransform() {
		state.transforms.push({ type: '', options: {} })
		query.updateTransforms(state.transforms)
	}
	function removeTransformAt(removedTransformIdx) {
		state.transforms.splice(removedTransformIdx, 1)
		query.updateTransforms(state.transforms)
	}
	function updateTransformAt(updatedTransformIdx, newTransform) {
		state.transforms.splice(updatedTransformIdx, 1, newTransform)
		query.updateTransforms(state.transforms)
	}

	async function inferJoins() {
		const joins = await inferJoinsFromColumns(state)
		const newJoins = joins.filter((join) => {
			return !state.joins.some(
				(j) =>
					j.left_table.table === join.left_table.table &&
					j.right_table.table === join.right_table.table
			)
		})
		state.joins.push(...newJoins)
	}

	return state
}

function makeGroupedColumnOptions(options) {
	const columnsByTable = options.reduce((acc, column) => {
		if (!acc[column.table_label]) acc[column.table_label] = []
		acc[column.table_label].push(column)
		return acc
	}, {})

	return Object.entries(columnsByTable).map(([table_label, columns]) => {
		if (!columns.length) return { group: table_label, items: [] }
		columns.splice(0, 0, {
			...NEW_COLUMN,
			table: columns[0].table,
			column: 'count',
			type: 'Integer',
			label: 'Count of Rows',
			alias: 'Count of Rows',
			aggregation: 'count',
		})
		return {
			group: table_label,
			items: columns.map(makeColumnOption),
		}
	})
}

export function hasTablesChanged(newJson, oldJson) {
	if (!oldJson) return true
	const newTables = getSelectedTables(newJson)
	const oldTables = getSelectedTables(oldJson)
	return !areDeeplyEqual(newTables, oldTables)
}

export function getSelectedTables(queryJson) {
	if (!queryJson) return []
	const tables = [queryJson.table.table, ...queryJson.joins.map((join) => join.right_table.table)]
	return tables.filter((table) => table)
}
