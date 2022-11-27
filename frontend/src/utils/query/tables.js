import { computed } from 'vue'
import { safeJSONParse } from '@/utils'

export function useQueryTables(query) {
	query.fetchTables.submit()
	return {
		data: computed(() =>
			query.doc?.tables.map((table) => {
				return {
					...table,
					value: table.table,
					join: table.join ? safeJSONParse(table.join) : null,
				}
			})
		),
		options: computed(() => {
			return query.fetchTables.data?.message.map((table) => ({
				...table,
				value: table.table,
			}))
		}),
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
