import { computed } from 'vue'
import {
	carriedCurrency,
	numberFormatOf,
	numberFormatter,
	type NumberFormatter,
} from '../charts/number_format'
import type { NumberFormat } from '../types/chart.types'
import type { DataFormat, QueryResultRow } from '../types/query.types'

export type TableNumberFormatSource = {
	numberFormat?: NumberFormat
	numberFormats?: Record<string, NumberFormat>
	columnFormats?: Record<string, DataFormat>
	rows?: QueryResultRow[]
	numberColumns: string[]
}

/**
 * How a grid prints its numbers, the way every chart does: it states the policy
 * and the one resolver answers it. A column is looked up by name, which is what
 * the Measure behind it is called. A cell reads its currency off its own row, and
 * a column total off every row it sums, so a total over rows in different
 * currencies prints bare. A row total sums every number column, so it prints the
 * way they all do, and under the table's own default when they differ.
 *
 * Each formatter is kept per currency, so every reactive read happens where the
 * computed runs: one read inside a returned function would keep a formatter of
 * the settings it first saw.
 */
export function useTableNumberFormats(source: () => TableNumberFormatSource) {
	const plain = computed(() => numberFormatter(source().numberFormat))

	const cell = computed(() => {
		const { numberFormat, numberFormats, columnFormats = {}, rows = [] } = source()
		const config = { number_format: numberFormat, number_formats: numberFormats }
		const cache = new Map<string, NumberFormatter>()
		return (columnName: string, row?: QueryResultRow): NumberFormatter => {
			const over = row ? [row] : rows
			const key = `${columnName}\0${carriedCurrency(over, columnName)}`
			let format = cache.get(key)
			if (!format) {
				format = numberFormatter(
					config,
					{ measure_name: columnName, format: columnFormats[columnName] },
					over,
				)
				cache.set(key, format)
			}
			return format
		}
	})

	const rowTotal = computed(() => {
		const {
			numberFormat,
			numberFormats,
			columnFormats = {},
			rows = [],
			numberColumns,
		} = source()
		const config = { number_format: numberFormat, number_formats: numberFormats }
		const cellFormat = cell.value
		const fallback = plain.value
		const cache = new Map<string, NumberFormatter>()
		return (row?: QueryResultRow): NumberFormatter => {
			const over = row ? [row] : rows
			const key = numberColumns.map((name) => carriedCurrency(over, name)).join('\0')
			let format = cache.get(key)
			if (!format) {
				const printed = new Set(
					numberColumns.map((name) =>
						JSON.stringify(
							numberFormatOf(
								config,
								{ measure_name: name, format: columnFormats[name] },
								over,
							),
						),
					),
				)
				format = printed.size === 1 ? cellFormat(numberColumns[0], row) : fallback
				cache.set(key, format)
			}
			return format
		}
	})

	return { plain, cell, rowTotal }
}
