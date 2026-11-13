// The data source and table that `ImportTableDialog` picks for an import. They
// are one selection, so the row count shown always belongs to the picked table.

import { reactive, watch } from 'vue'
import { getRowCount } from '../data_source/tables'

export function useTableSelection() {
	const selection = reactive({
		data_source: '',
		table_name: '',
		// undefined, not zero: "0 rows" before the count arrives looks like an
		// empty table
		table_row_count: undefined as number | undefined,
		pickSource(data_source: string) {
			selection.data_source = data_source
			selection.table_name = ''
		},
		pickTable(table_name: string) {
			selection.table_name = table_name
		},
		reset() {
			selection.pickSource('')
		},
	})

	// Responses can arrive out of order, so only the latest request may write.
	let asked = 0
	watch(
		() => [selection.data_source, selection.table_name] as const,
		([data_source, table_name]) => {
			const ask = ++asked
			selection.table_row_count = undefined
			if (!data_source || !table_name) return
			getRowCount(data_source, table_name).then((count) => {
				if (ask === asked) selection.table_row_count = count
			})
		},
	)

	return selection
}
