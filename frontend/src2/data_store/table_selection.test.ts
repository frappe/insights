import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

// what each count asked for answers with, settled by the case
const counts = vi.hoisted(() => new Map<string, (count: number) => void>())

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: (method: string, args: any) => {
		if (method !== 'insights.api.data_sources.get_data_source_table_row_count') {
			return Promise.resolve([])
		}
		return new Promise((resolve) =>
			counts.set(`${args.data_source}/${args.table_name}`, resolve),
		)
	},
}))

import { useTableSelection } from './table_selection'

const settled = async () => {
	for (let i = 0; i < 5; i++) await nextTick()
}

beforeEach(() => counts.clear())

// `ImportTableDialog.vue`'s two comboboxes write the source and the table the
// import copies, and the dialog prints the count under the table.

describe('the table an import copies', () => {
	// @feature data-store.import-table
	it('is cleared with its count when the data source changes under it', async () => {
		const selection = useTableSelection()
		selection.pickSource('DS1')
		selection.pickTable('T1')
		await settled()
		counts.get('DS1/T1')!(1234)
		await settled()
		expect(selection.table_row_count).toBe(1234)

		selection.pickSource('DS2')
		await settled()

		expect(selection.table_name).toBe('')
		expect(selection.table_row_count).toBeUndefined()
	})

	// @feature data-store.import-table
	it('prints the count of the table picked last, whichever count lands last', async () => {
		const selection = useTableSelection()
		selection.pickSource('DS1')
		selection.pickTable('T1')
		await settled()
		selection.pickTable('T2')
		await settled()

		counts.get('DS1/T2')!(20)
		await settled()
		counts.get('DS1/T1')!(1234)
		await settled()

		expect(selection.table_name).toBe('T2')
		expect(selection.table_row_count).toBe(20)
	})
})
