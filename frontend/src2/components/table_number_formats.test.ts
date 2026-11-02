import { describe, expect, it } from 'vitest'
import { effectScope, reactive } from 'vue'
import { useTableNumberFormats, type TableNumberFormatSource } from './table_number_formats'

describe('the numbers of a grid', () => {
	// @feature charts.table-totals
	it('print under the settings the author changed them to', () => {
		const source = reactive<TableNumberFormatSource>({
			numberFormat: { decimals: 0 },
			rows: [{ Revenue: 100.25, Outstanding: 20 }],
			numberColumns: ['Revenue', 'Outstanding'],
		})
		const scope = effectScope()
		const formats = scope.run(() => useTableNumberFormats(() => source))!
		const row = source.rows![0]
		expect(formats.cell.value('Revenue', row)(100.25)).toBe('100')
		expect(formats.rowTotal.value(row)(120.25)).toBe('120')

		source.numberFormat = { decimals: 1, prefix: '~' }

		expect(formats.cell.value('Revenue', row)(100.25)).toBe('~100.3')
		expect(formats.rowTotal.value(row)(120.25)).toBe('~120.3')
		expect(formats.plain.value(120.25)).toBe('~120.3')
		scope.stop()
	})
})
