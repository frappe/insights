import { computed } from 'vue'
import { safeJSONParse } from '@/utils'

export function useQueryTables(query) {
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
		validateRemoveTable({ table, label }) {
			const columnsFromTable = query.doc.columns.filter((c) => c.table === table)
			if (columnsFromTable.length > 0) {
				return {
					title: 'Cannot remove table',
					message: `Remove dimensions and metrics associated with ${label} table and try again`,
					appearance: 'error',
				}
			}
		},
	}
}
