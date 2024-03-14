import { safeJSONParse } from '@/utils'
import { computed } from 'vue'

export function useQueryTables(query) {
	query.fetchTables.submit()

	const data = computed(() =>
		query.doc?.tables.map((table) => {
			return {
				...table,
				value: table.table,
				join: table.join ? safeJSONParse(table.join) : null,
			}
		})
	)
	const sourceTables = computed(() =>
		query.fetchTables.data
			?.filter((t) => t.table != query.doc.name)
			.map((table) => ({
				...table,
				value: table.table,
				description: table.is_query_based ? 'Query' : '',
			}))
	)

	const joinOptions = computed(() => {
		// any two table/query can be joined from the same data source
		return sourceTables.value
	})

	const newTableOptions = computed(() => {
		if (query.doc?.tables?.length == 0) {
			return sourceTables.value
		}
		// only return tables that are already selected in the query
		// to ensure correct chaining of joins
		const tables = query.doc?.tables.map((t) => ({ label: t.label, value: t.table }))
		const joinedTables = query.doc?.tables.reduce((acc, table) => {
			if (table.join) {
				const join = safeJSONParse(table.join)
				acc.push({ label: join.with.label, value: join.with.table })
			}
			return acc
		}, [])
		return [...tables, ...joinedTables]
	})

	return {
		data,
		newTableOptions,
		joinOptions,
		validateRemoveTable({ table, label }) {
			const columnsFromTable = query.doc.columns.filter((c) => c.table === table)
			// allow removing table if it has been selected twice
			const tableCount = query.doc.tables.filter((t) => t.table === table).length
			if (columnsFromTable.length > 0 && tableCount == 1) {
				return {
					title: 'Cannot remove table',
					message: `Remove dimensions and metrics associated with ${label} table and try again`,
					variant: 'warning',
				}
			}
		},
	}
}
