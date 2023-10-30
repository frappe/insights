import { FIELDTYPES } from '@/utils'
import { NEW_COLUMN, NEW_JOIN } from './constants'

export function makeNewColumn(newColumn) {
	const isDate = FIELDTYPES.DATE.includes(newColumn.type)
	const isNumber = FIELDTYPES.NUMBER.includes(newColumn.type)
	return {
		...NEW_COLUMN,
		...newColumn,
		granularity: isDate ? 'Month' : '',
		aggregation: isNumber ? 'sum' : '',
	}
}

export function inferJoinsFromColumns(builderQuery, tableMeta) {
	const newJoins = []

	const mainTable = builderQuery.table
	if (!mainTable.table) return newJoins

	const columns = [
		...builderQuery.columns,
		...builderQuery.filters.map((f) => f.column).filter((c) => c.table && c.column),
	]
	const columnByTable = columns.reduce((acc, column) => {
		if (!acc[column.table]) acc[column.table] = null
		acc[column.table] = column
		return acc
	}, {})

	Object.values(columnByTable).forEach((column) => {
		if (column.table == mainTable.table) return

		// check if the column has a relation with main table, if so add the join
		const relation = getRelation(mainTable.table, column.table, tableMeta)
		if (relation) {
			newJoins.push(makeJoinFromRelation(relation, tableMeta))
			return
		}

		// check if the column has a relation with any other table, if so add the join
		Object.keys(columnByTable).some((table) => {
			if (table === column.table) return false
			if (table === mainTable.table) return false
			const relation = getRelation(table, column.table, tableMeta)
			if (relation) {
				newJoins.push(makeJoinFromRelation(relation, tableMeta))
				return true
			}
		})
	})

	return newJoins
}

function makeJoinFromRelation(relation, tableMeta) {
	const leftTable = tableMeta.find((m) => m.table === relation.primary_table)
	const rightTable = tableMeta.find((m) => m.table === relation.foreign_table)
	const leftColumn = leftTable.columns.find((c) => c.column === relation.primary_column)
	const rightColumn = rightTable.columns.find((c) => c.column === relation.foreign_column)
	return {
		...NEW_JOIN,
		left_table: leftTable,
		left_column: leftColumn,
		right_table: rightTable,
		right_column: rightColumn,
	}
}

function getRelation(tableOne, tableTwo, tableMeta) {
	const tableOneMeta = tableMeta.find((m) => m.table === tableOne)
	if (!tableOneMeta) return null
	return tableOneMeta.relations.find((r) => r.foreign_table === tableTwo)
}

export function inferJoinForTable(newTable, builderQuery, tableMeta) {
	const mainTable = builderQuery.table
	if (!mainTable.table) return null

	const relation = getRelation(mainTable.table, newTable.table, tableMeta)
	if (relation) return makeJoinFromRelation(relation, tableMeta)

	// find a relation with any other joined table
	let relationWithJoinedTable = null
	builderQuery.joins.some((join) => {
		const relation = getRelation(join.left_table, newTable.table, tableMeta)
		if (relation) {
			relationWithJoinedTable = relation
			return true
		}
	})

	if (relationWithJoinedTable) {
		return makeJoinFromRelation(relationWithJoinedTable, tableMeta)
	}

	return null
}

export function isTableAlreadyAdded(builderQuery, newTable) {
	const table = builderQuery.table
	if (table.table === newTable.table) return true
	return builderQuery.joins.some((join) => join.right_table === newTable.table)
}
