// The table an import copies, as `ImportTableDialog` picks it: a table of a data
// source. The two are one selection, so the count printed under it is always
// the count of both.

import { reactive, watch } from 'vue'
import { getRowCount } from '../data_source/tables'

export function useTableSelection() {
	const selection = reactive({
		data_source: '',
		table_name: '',
		// undefined and not zero: the count is not known yet, and "0 rows" under a
		// table nobody counted reads as an empty table
		table_row_count: undefined as number | undefined,
		// a table belongs to its source, so another source leaves none picked
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

	// The count that lands last need not be the one asked last, so only the
	// latest ask may write.
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
