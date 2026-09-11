import { describe, expect, it } from 'vitest'
import type { ChartConfig } from '../types/chart.types'
import {
	LAST_YEAR,
	buildWindowSpan,
	formatWindowLabel,
	labelWindowRows,
	parseWindowSpan,
	choiceOfPeriod,
	previousWindowShift,
	periodOf,
	periodOfChoice,
	windowChoiceGroups,
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

describe('the periods the picker writes', () => {
	// The server parses these strings, so this list is the contract. Every one of
	// them is a span `get_window` reads: `<unit> to date`, `current <unit>`,
	// `last <n> <unit>s`, and the `(include current)` suffix. The grain family
	// writes no span at all — it groups by the grain and filters nothing.
	it('writes one period per choice, and reads its own choice back off it', () => {
		const periods = windowChoices()
			.map((choice) => choice.value)
			.map((choice) => [choice, periodOfChoice(choice)] as const)

		expect(Object.fromEntries(periods)).toEqual({
			'to date:week': { span: 'week to date' },
			'to date:month': { span: 'month to date' },
			'to date:quarter': { span: 'quarter to date' },
			'to date:year': { span: 'year to date' },
			'to date:fiscal year': { span: 'fiscal year to date' },
			'current:day': { span: 'current day' },
			'current:week': { span: 'current week' },
			'current:month': { span: 'current month' },
			'current:quarter': { span: 'current quarter' },
			'current:year': { span: 'current year' },
			'current:fiscal year': { span: 'current fiscal year' },
			'last:day': { span: 'last 3 days' },
			'last:week': { span: 'last 3 weeks' },
			'last:month': { span: 'last 3 months' },
			'last:quarter': { span: 'last 3 quarters' },
			'last:year': { span: 'last 3 years' },
			'last:fiscal year': { span: 'last 3 fiscal years' },
			'grain:day': { grain: 'day' },
			'grain:week': { grain: 'week' },
			'grain:month': { grain: 'month' },
			'grain:quarter': { grain: 'quarter' },
			'grain:year': { grain: 'year' },
			'grain:fiscal year': { grain: 'fiscal_year' },
		})

		periods.forEach(([choice, period]) => expect(choiceOfPeriod(period)).toBe(choice))
	})

	it('never writes both a span and a grain, so a card groups once', () => {
		expect(periodOfChoice('grain:month', { span: 'last 3 months' })).toEqual({ grain: 'month' })
		expect(periodOfChoice('last:month', { grain: 'month' })).toEqual({ span: 'last 3 months' })
	})

	it('keeps the run an author already set when they change the unit', () => {
		expect(periodOfChoice('last:week', { span: 'last 6 months (include current)' })).toEqual({
			span: 'last 6 weeks (include current)',
		})
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
		expect(choiceOfPeriod({ span: 'next 2 months' })).toBe('next 2 months')
		expect(periodOfChoice('next 2 months')).toEqual({ span: 'next 2 months' })
	})

	it('leaves a grain it has no choice for standing as its own choice', () => {
		// An hourly card, authored before periods existed.
		expect(choiceOfPeriod({ grain: 'hour' })).toBe('hour')
	})
})

describe('the headings the picker lists under', () => {
	it('puts every choice under exactly one heading', () => {
		// A family added to the copy and left out of the groups would be
		// unpickable, and nothing else would say so.
		const grouped = windowChoiceGroups().flatMap((group) =>
			group.options.map((option) => option.value),
		)

		expect(grouped.sort()).toEqual(
			windowChoices()
				.map((choice) => choice.value)
				.sort(),
		)
	})

	it('heads every family, and offers nothing outside one', () => {
		expect(windowChoiceGroups().map((group) => group.group)).toEqual([
			'Up to today',
			'Whole current period',
			'Previous periods',
			'Latest in the data',
		])
	})
})

describe('the period a card reads', () => {
	it('lifts the date column granularity of a card written before periods existed', () => {
		const card = {
			date_column: { column_name: 'created_at', granularity: 'month' },
		} as any

		expect(periodOf(card)).toEqual({ grain: 'month' })
	})

	it('lets the period win, so a migrated card is read once', () => {
		const card = {
			date_column: { column_name: 'created_at', granularity: 'month' },
			window: { span: 'last 3 months' },
		} as any

		expect(periodOf(card)).toEqual({ span: 'last 3 months' })
	})

	it('names no period for a card with no date column', () => {
		expect(periodOf({ date_column: {} } as any)).toBeUndefined()
	})

	it('offers no "no period" choice, because a column that groups nothing does nothing', () => {
		expect(choiceOfPeriod(undefined)).toBe('')
		expect(periodOfChoice('')).toBeUndefined()
		expect(windowChoices().every((choice) => choice.value.includes(':'))).toBe(true)
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

	it('reads an unnumbered run as one period, the way `get_window` reads it', () => {
		// A hand-written span the picker never offers. `_span_periods` counts it
		// as one, so the card fetches the month before — and a caption that could
		// not read the span left that figure unworded.
		expect(previousWindowShift('last month')).toEqual({ unit: 'month', count: -1 })
		expect(previousWindowShift('last fiscal year')).toEqual({
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
