import { describe, expect, it } from 'vitest'
import session from '../session'
import {
	axisChart,
	bubbleChart,
	donutChart,
	funnelChart,
	heatmapChart,
	mapChart,
	sankeyChart,
} from './adapter/fixtures'
import { adaptChart } from './adapter'
import type { ChartAdapterInput } from './adapter/types'
import {
	defaultDecimals,
	printNumber,
	numberFormatOf,
	numberFormatter,
	readNumberFormat,
} from './number_format'

// The one policy, tested where it is decided. Every chart and the grid read
// their numbers through `numberFormatter`, so what holds here holds everywhere.

const measure = (name: string, format?: 'currency' | 'percent') => ({
	measure_name: name,
	format,
})

describe('what the locale says', () => {
	it('groups the digits and keeps what the number carries, up to two places', () => {
		const print = numberFormatter()
		expect(print(1234567)).toBe('1,234,567')
		expect(print(1234.5)).toBe('1,234.5')
		expect(print(1.23456)).toBe('1.23')
	})

	it('says nothing about a value that is not a number', () => {
		const print = numberFormatter()
		expect(print(null as any)).toBe('')
		expect(print(undefined as any)).toBe('')
		expect(print('elsewhere' as any)).toBe('')
	})
})

describe("what the Measure's own format says", () => {
	it('scales a percent Measure and states the unit', () => {
		expect(numberFormatter(null, measure('rate', 'percent'))(0.42)).toBe('42%')
	})

	it('prints the site currency where the site puts it', () => {
		session.site.currency_symbol = '₹'
		session.site.currency_symbol_on_right = false
		expect(numberFormatter(null, measure('revenue', 'currency'))(1200)).toBe('₹ 1,200')

		session.site.currency_symbol_on_right = true
		expect(numberFormatter(null, measure('revenue', 'currency'))(1200)).toBe('1,200 ₹')

		session.site.currency_symbol = ''
		session.site.currency_symbol_on_right = false
	})
})

describe('what the chart says', () => {
	it('shortens, fixes the places, and states its own units', () => {
		const config = {
			number_format: { shorten: true, decimals: 2, prefix: '$', suffix: '/mo' },
		}
		expect(numberFormatter(config, measure('revenue'))(1234567)).toBe('$1.23M/mo')
	})

	it('prints no decimals when it asks for none', () => {
		expect(numberFormatter({ number_format: { decimals: 0 } })(1234.56)).toBe('1,235')
	})

	it('stands in for the unit the Measure states', () => {
		const config = { number_format: { suffix: ' pts' } }
		expect(numberFormatter(config, measure('rate', 'percent'))(0.42)).toBe('42 pts')
	})

	it('scales a percent Measure whatever it prints around it', () => {
		expect(
			numberFormatOf({ number_format: { suffix: 'x' } }, measure('rate', 'percent')),
		).toEqual({ prefix: '', suffix: 'x', scale: 100 })
	})
})

describe('a precision the number cannot print', () => {
	// `Intl.NumberFormat` throws outside 0..20 places, which takes down the whole
	// chart rather than one value. The resolver clamps, so no config can do it.
	it('reads a negative number of places as none', () => {
		expect(numberFormatter({ number_format: { decimals: -2 } })(1234.56)).toBe('1,235')
	})

	it('reads more places than the printer holds as the most it holds', () => {
		expect(readNumberFormat({ decimals: 40 }).decimals).toBe(20)
	})

	it('reads a fractional number of places as the whole one under it', () => {
		expect(readNumberFormat({ decimals: 2.7 }).decimals).toBe(2)
	})
})

describe('the precision an unstated one falls back on', () => {
	// One function answers this for every field that shows it, so the chart's
	// own precision and a Measure's cannot state different defaults.
	it('is the one place a shortened number prints', () => {
		expect(defaultDecimals(true)).toBe(1)
		expect(printNumber(1234.56, { scale: 1, shorten: true })).toBe('1.2K')
	})

	it('is nothing when the number does not shorten, because the locale picks it', () => {
		expect(defaultDecimals(false)).toBeUndefined()
		expect(defaultDecimals(undefined)).toBeUndefined()
	})
})

describe('what one Measure says', () => {
	it('overrides the chart, key by key', () => {
		const config = {
			number_format: { shorten: true, prefix: '$' },
			number_formats: { refunds: { prefix: '-$' } },
		}
		expect(numberFormatter(config, measure('revenue'))(1234567)).toBe('$1.2M')
		// `shorten` still comes from the chart: an override replaces one key, not all of them.
		expect(numberFormatter(config, measure('refunds'))(1234567)).toBe('-$1.2M')
	})

	it('clears an inherited affix with an empty one', () => {
		const config = {
			number_format: { prefix: '$' },
			number_formats: { refunds: { prefix: '' } },
		}
		expect(numberFormatter(config, measure('refunds'))(1200)).toBe('1,200')
	})
})

describe('the spellings an older release wrote', () => {
	it("reads a table's compact_numbers as the chart's own shorten", () => {
		expect(readNumberFormat({ compact_numbers: true })).toEqual({ shorten: true })
	})

	it("reads a Number chart's chart-level settings as its default", () => {
		const config = { shorten_numbers: true, decimal: 1, prefix: '$' }
		expect(numberFormatter(config, measure('revenue'))(1234567)).toBe('$1.2M')
	})

	it("reads a Number chart's per-value settings as that Measure's own", () => {
		const config = {
			shorten_numbers: true,
			number_columns: [measure('revenue'), measure('refunds')],
			number_column_options: [{}, { prefix: '-$', decimal: 2 }],
		}
		expect(numberFormatter(config, measure('refunds'))(1234567)).toBe('-$1.23M')
		expect(numberFormatter(config, measure('revenue'))(1234567)).toBe('1.2M')
	})

	it('is overridden by the spelling the forms write now', () => {
		const config = {
			shorten_numbers: true,
			prefix: '$',
			number_format: { shorten: false },
			number_formats: { revenue: { prefix: '€' } },
		}
		expect(numberFormatter(config, measure('revenue'))(1200)).toBe('€1,200')
	})
})

// Every type that draws a plot hands the formatter to v2 rather than printing a
// number of its own. The Number card is the exception the module states, and the
// Table hands the grid the policy instead of a function.
const plotted: Array<[string, ChartAdapterInput, string]> = [
	['Bar', axisChart({ type: 'Bar', dimension: 'month', measures: ['revenue'] }), 'yAxis'],
	['Line', axisChart({ type: 'Line', dimension: 'month', measures: ['revenue'] }), 'yAxis'],
	['Donut', donutChart({ category: 'region', measure: 'revenue' }), 'props'],
	['Funnel', funnelChart({ dimension: 'stage', measure: 'count' }), 'props'],
	['Sankey', sankeyChart({ source: 'from', target: 'to', measure: 'amount' }), 'props'],
	['Heatmap', heatmapChart({ x: 'day', y: 'hour', measure: 'orders' }), 'props'],
	['Bubble', bubbleChart({ x: 'cost', y: 'revenue', size: 'orders' }), 'props'],
	['Map', mapChart({ regions: [{ region: 'India', value: 30 }] }), 'props'],
]

describe.each(plotted)('the %s chart', (_type, input, where) => {
	it('prints its numbers through the resolver', () => {
		const filler = adaptChart(input)
		if (!filler) throw new Error('the adapter drew nothing for this Chart')

		const format = where === 'yAxis' ? filler.props.yAxis?.format : filler.props.format
		expect(typeof format).toBe('function')
		expect(format(1234567)).toBe('1,234,567')
	})
})
