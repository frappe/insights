import { describe, expect, it } from 'vitest'
import type { ChartConfig } from '../types/chart.types'
import {
	LAST_YEAR,
	buildWindowSpan,
	formatWindowLabel,
	labelWindowRows,
	parseWindowSpan,
	previousWindowShift,
	spanOfChoice,
	windowChoiceOf,
	windowChoices,
	windowShiftLabel,
} from './window'

/** A number card reading `span` over `column`. */
function windowedCard(span: string, column = 'created_at'): ChartConfig {
	return {
		number_columns: [],
		number_column_options: [],
		sparkline: false,
		date_column: { dimension_name: column, column_name: column, data_type: 'Date' },
		window: { span },
	} as unknown as ChartConfig
}

describe('the spans the picker writes', () => {
	// The server parses these strings, so this list is the contract. Every one of
	// them is a span `get_window` reads: `<unit> to date`, `current <unit>`,
	// `last <n> <unit>s`, and the `(include current)` suffix.
	it('writes one string per choice, and reads its own choice back off it', () => {
		const spans = windowChoices()
			.map((choice) => choice.value)
			.filter((choice) => choice !== 'none')
			.map((choice) => [choice, spanOfChoice(choice)] as const)

		expect(Object.fromEntries(spans)).toEqual({
			'to date:week': 'week to date',
			'to date:month': 'month to date',
			'to date:quarter': 'quarter to date',
			'to date:year': 'year to date',
			'to date:fiscal year': 'fiscal year to date',
			'current:day': 'current day',
			'current:week': 'current week',
			'current:month': 'current month',
			'current:quarter': 'current quarter',
			'current:year': 'current year',
			'current:fiscal year': 'current fiscal year',
			'last:day': 'last 3 days',
			'last:week': 'last 3 weeks',
			'last:month': 'last 3 months',
			'last:quarter': 'last 3 quarters',
			'last:year': 'last 3 years',
			'last:fiscal year': 'last 3 fiscal years',
		})

		spans.forEach(([choice, span]) => expect(windowChoiceOf(span)).toBe(choice))
	})

	it('keeps the run an author already set when they change the unit', () => {
		expect(spanOfChoice('last:week', 'last 6 months (include current)')).toBe(
			'last 6 weeks (include current)',
		)
	})

	it('names one period without a count, so `last 1 months` is never written', () => {
		expect(buildWindowSpan({ shape: 'last', unit: 'month', count: 1 })).toBe('last 1 month')
	})

	it('reads a span back into the parts the form edits', () => {
		expect(parseWindowSpan('last 3 months (include current)')).toEqual({
			shape: 'last',
			unit: 'month',
			count: 3,
			includeCurrent: true,
		})
		expect(parseWindowSpan('fiscal year to date')).toEqual({
			shape: 'to date',
			unit: 'fiscal year',
		})
		expect(parseWindowSpan('current quarter')).toEqual({ shape: 'current', unit: 'quarter' })
	})

	it('reads nothing out of a span it did not write', () => {
		expect(parseWindowSpan('last 3 fortnights')).toBeUndefined()
		expect(parseWindowSpan('whenever')).toBeUndefined()
		expect(parseWindowSpan('')).toBeUndefined()
	})

	it('leaves a span it cannot read standing as its own choice', () => {
		// Hand-authored, or written by a later release. Opening the form must not
		// drop it silently.
		expect(windowChoiceOf('next 2 months')).toBe('next 2 months')
		expect(spanOfChoice('next 2 months')).toBe('next 2 months')
	})
})

describe('the window a comparison shifts to', () => {
	it('moves the span back by its own length, so the two windows never overlap', () => {
		expect(previousWindowShift('month to date')).toEqual({ unit: 'month', count: -1 })
		expect(previousWindowShift('current quarter')).toEqual({ unit: 'quarter', count: -1 })
		expect(previousWindowShift('last 3 months')).toEqual({ unit: 'month', count: -3 })
		// The current period is part of the window, so the window before it is one
		// period further back.
		expect(previousWindowShift('last 3 months (include current)')).toEqual({
			unit: 'month',
			count: -4,
		})
		expect(previousWindowShift('fiscal year to date')).toEqual({
			unit: 'fiscal year',
			count: -1,
		})
	})

	it('names no shift for a card with no window', () => {
		expect(previousWindowShift(undefined)).toBeUndefined()
	})
})

describe('what a shifted window is called', () => {
	it('words the shift, so a year back needs no typing', () => {
		expect(windowShiftLabel(LAST_YEAR)).toBe('vs same period last year')
		expect(windowShiftLabel({ unit: 'month', count: -1 })).toBe('vs same period last month')
		expect(windowShiftLabel({ unit: 'month', count: -3 })).toBe('vs same period 3 months ago')
		expect(windowShiftLabel({ unit: 'fiscal year', count: -1 })).toBe(
			'vs same period last fiscal year',
		)
	})

	it('says nothing when the comparison names no window to shift to', () => {
		expect(windowShiftLabel(undefined)).toBeUndefined()
		expect(windowShiftLabel({ unit: 'month', count: 0 })).toBeUndefined()
		expect(windowShiftLabel({ unit: 'fortnight', count: -1 })).toBeUndefined()
	})
})

describe('how a window prints', () => {
	it('names the period, not the date the period starts on', () => {
		expect(formatWindowLabel('month to date', '2026-08-01')).toBe('August, 2026')
		expect(formatWindowLabel('current quarter', '2026-07-01')).toBe('Q3, 2026')
		expect(formatWindowLabel('year to date', '2026-01-01')).toBe('2026')
	})

	it('names the whole run of a span covering several periods', () => {
		// Printing `June, 2026` for a June-to-August window reads as June's own
		// number, which is the reading the window exists to replace.
		expect(formatWindowLabel('last 3 months', '2026-06-01')).toBe('June, 2026 – August, 2026')
		expect(formatWindowLabel('last 3 months (include current)', '2026-05-01')).toBe(
			'May, 2026 – August, 2026',
		)
		expect(formatWindowLabel('last 2 quarters', '2026-01-01')).toBe('Q1, 2026 – Q2, 2026')
	})

	it('leaves a value alone when the span says nothing about it', () => {
		expect(formatWindowLabel('whenever', '2026-08-01')).toBe('2026-08-01')
		expect(formatWindowLabel('month to date', null)).toBeNull()
	})
})

describe('the rows a windowed card draws', () => {
	it('reads the window column as a period', () => {
		const rows = [
			{ created_at: '2026-07-01', Revenue: 100 },
			{ created_at: '2026-08-01', Revenue: 120 },
		]

		expect(labelWindowRows(rows, 'Number', windowedCard('month to date'))).toEqual([
			{ created_at: 'July, 2026', Revenue: 100 },
			{ created_at: 'August, 2026', Revenue: 120 },
		])
	})

	it('leaves every other card and every unwindowed one exactly as it was', () => {
		const rows = [{ created_at: '2026-08-01', Revenue: 120 }]
		const card = windowedCard('month to date')

		expect(labelWindowRows(rows, 'Bar', card)).toBe(rows)
		expect(labelWindowRows(rows, 'Number', { ...card, window: undefined } as any)).toBe(rows)
	})
})
