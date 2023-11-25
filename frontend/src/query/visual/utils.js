import { FIELDTYPES } from '@/utils'
import { call } from 'frappe-ui'
import { NEW_COLUMN, NEW_JOIN } from './constants'

export function makeNewColumn(newColumn) {
	const isDate = FIELDTYPES.DATE.includes(newColumn.type)
	const isNumber = FIELDTYPES.NUMBER.includes(newColumn.type)
	return {
		...NEW_COLUMN,
		...newColumn,
		granularity: newColumn.granularity || (isDate ? 'Month' : ''),
		aggregation: newColumn.aggregation || (isNumber ? 'sum' : ''),
	}
}

export async function inferJoinsFromColumns(assistedQuery) {
	const newJoins = []

	const data_source = assistedQuery.data_source
	const mainTable = assistedQuery.table
	if (!mainTable.table) return newJoins

	const columns = [
		...assistedQuery.columns.filter((c) => c.table && c.column),
		...assistedQuery.filters.map((f) => f.column).filter((c) => c.table && c.column),
	]
	const columnByTable = columns.reduce((acc, column) => {
		acc[column.table] = column
		return acc
	}, {})

	for (const column of Object.values(columnByTable)) {
		if (column.table == mainTable.table) continue

		// check if the column has a relation with main table, if so add the join
		const relation = await getRelation(mainTable.table, column.table, data_source)
		if (relation) {
			newJoins.push(makeJoinFromRelation(relation))
			continue
		}

		// check if the column has a relation with any other table, if so add the join
		for (const table of Object.keys(columnByTable)) {
			if (table === column.table) continue
			if (table === mainTable.table) continue
			const relation = await getRelation(table, column.table, data_source)
			if (relation) {
				newJoins.push(makeJoinFromRelation(relation))
				break
			}
		}
	}

	return newJoins
}

function makeJoinFromRelation(relation) {
	return {
		...NEW_JOIN,
		left_table: {
			table: relation.primary_table,
			label: relation.primary_table_label,
		},
		left_column: {
			table: relation.primary_table,
			column: relation.primary_column,
		},
		right_table: {
			table: relation.foreign_table,
			label: relation.foreign_table_label,
		},
		right_column: {
			table: relation.foreign_table,
			column: relation.foreign_column,
		},
	}
}

const relations_cache = {}
async function getRelation(tableOne, tableTwo, data_source) {
	const cache_key = `${data_source}-${tableOne}-${tableTwo}`
	if (relations_cache[cache_key]) {
		return relations_cache[cache_key]
	}
	relations_cache[cache_key] = await call('insights.api.data_sources.get_relation', {
		data_source: data_source,
		table_one: tableOne,
		table_two: tableTwo,
	})
	return relations_cache[cache_key]
}

export async function inferJoinForTable(newTable, assistedQuery) {
	const mainTable = assistedQuery.table
	const data_source = assistedQuery.data_source
	if (!mainTable.table) return null

	const relation = await getRelation(mainTable.table, newTable.table, data_source)
	if (relation) return makeJoinFromRelation(relation)

	// find a relation with any other joined table
	let relationWithJoinedTable = null
	for (const join of assistedQuery.joins) {
		const relation = await getRelation(join.right_table.table, newTable.table, data_source)
		if (relation) {
			return makeJoinFromRelation(relation)
		}
	}

	return null
}

export function isTableAlreadyAdded(assistedQuery, newTable) {
	const table = assistedQuery.table
	if (table.table === newTable.table) return true
	return assistedQuery.joins.some((join) => join.right_table.table === newTable.table)
}

export function sanitizeQueryJSON(queryJson) {
	// backward compatibility with old json
	if (queryJson.measures.length || queryJson.dimensions.length) {
		// copy measures and dimensions to columns
		queryJson.measures.forEach((m) => {
			if (!queryJson.columns.find((col) => col.label === m.label)) {
				queryJson.columns.push(m)
			}
		})
		queryJson.dimensions.forEach((d) => {
			if (!queryJson.columns.find((col) => col.label === d.label)) {
				queryJson.columns.push(d)
			}
		})
	}
	if (queryJson.orders.length) {
		// set `order` property on columns
		queryJson.columns.forEach((c) => {
			const order = queryJson.orders.find((o) => o.label === c.label)
			if (order) c.order = order.order
		})
	}
	if (queryJson.filters.length) {
		// TODO:
		// some filters have column set as expression
		// we need to convert that into column expression object
	}

	if (!queryJson.limit) queryJson.limit = 100
	return { ...queryJson }
}
