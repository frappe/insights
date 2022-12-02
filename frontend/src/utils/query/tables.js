import { computed } from 'vue'
import { safeJSONParse } from '@/utils'

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
	const joinOptions = computed(() => {
		// any two table can be joined from the same data source
		// so, return all tables as join options
		return query.fetchTables.data?.message.map((table) => ({
			...table,
			value: table.table,
		}))
	})

	const newTableOptions = computed(() => {
		if (query.doc?.tables?.length == 0) {
			return joinOptions.value
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
			if (columnsFromTable.length > 0) {
				return {
					title: 'Cannot remove table',
					message: `Remove dimensions and metrics associated with ${label} table and try again`,
					appearance: 'warning',
				}
			}
		},
	}
}
