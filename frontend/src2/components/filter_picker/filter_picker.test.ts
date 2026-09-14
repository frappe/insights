import { describe, expect, it } from 'vitest'
import type { QueryResultColumn } from '../../types/query.types'
import {
	SPAN_UNITS,
	isPreset,
	numberPairValues,
	numberQuickValues,
	operatorOf,
	resolveSpan,
	spanLabel,
	toFilterArgs,
	unitOf,
} from './filter_picker'

// 2026-08-10 is a Monday. The same anchor the server's date range tests use, so
// the two tables below can be read against `TestDirectionalSpans` in
// `insights/tests/test_date_ranges.py` line by line.
const ANCHOR = '2026-08-10'

describe('the range a relative span covers', () => {
	// A directional span is N whole periods on one side of the anchor's own
	// period, which is never one of them. The picker prints this range under the
	// row it filters by, so it has to be the range the server filters to.
	// @feature query.filter-relative-date
	it('runs a forward span from the next period to the nth', () => {
		const spans = {
			'next 3 days': ['2026-08-11', '2026-08-13'],
			'next 3 months': ['2026-09-01', '2026-11-30'],
			'next 3 quarters': ['2026-10-01', '2027-06-30'],
			'next 3 years': ['2027-01-01', '2029-12-31'],
		}
		for (const [span, dates] of Object.entries(spans)) {
			expect(resolveSpan(span, ANCHOR), span).toEqual(dates)
		}
	})

	// @feature query.filter-relative-date
	it('runs a backward span from the nth period to the previous', () => {
		const spans = {
			'last 3 days': ['2026-08-07', '2026-08-09'],
			'last 3 months': ['2026-05-01', '2026-07-31'],
			'last 3 quarters': ['2025-10-01', '2026-06-30'],
			'last 3 years': ['2023-01-01', '2025-12-31'],
		}
		for (const [span, dates] of Object.entries(spans)) {
			expect(resolveSpan(span, ANCHOR), span).toEqual(dates)
		}
	})

	// dayjs starts a week on Sunday; the site says which day it starts on, and
	// `week_starts_on` comes with the site info so the browser counts the weeks
	// the server counts. The anchor is a Monday, and Monday is the default.
	// @feature settings.week-start
	it("measures a week span from the site's own week start", () => {
		expect(resolveSpan('next 3 weeks', ANCHOR)).toEqual(['2026-08-17', '2026-09-06'])
		expect(resolveSpan('last 3 weeks', ANCHOR)).toEqual(['2026-07-20', '2026-08-09'])
	})

	// A fiscal year is not a dayjs unit, so it had no range at all here. The
	// site's `fiscal_year_start` is what says where it begins — 1 April by default.
	// @feature settings.fiscal-year-start
	it("measures a fiscal year from the site's own fiscal year start", () => {
		expect(resolveSpan('fiscal year to date', ANCHOR)).toEqual(['2026-04-01', ANCHOR])
		expect(resolveSpan('current fiscal year', ANCHOR)).toEqual(['2026-04-01', '2027-03-31'])
		expect(resolveSpan('last 1 fiscal year', ANCHOR)).toEqual(['2025-04-01', '2026-03-31'])
	})

	// @feature query.filter-relative-date-include-current
	it('takes in the anchor period where the span asks for it', () => {
		expect(resolveSpan('last 3 months (include current)', ANCHOR)).toEqual([
			'2026-05-01',
			'2026-08-31',
		])
		expect(resolveSpan('next 3 months (include current)', ANCHOR)).toEqual([
			'2026-08-01',
			'2026-11-30',
		])
	})

	// @feature query.filter-relative-date
	it('covers the anchor period for a current span, and the period so far for a to-date one', () => {
		expect(resolveSpan('current month', ANCHOR)).toEqual(['2026-08-01', '2026-08-31'])
		expect(resolveSpan('month to date', ANCHOR)).toEqual(['2026-08-01', ANCHOR])
		expect(resolveSpan('year to date', ANCHOR)).toEqual(['2026-01-01', ANCHOR])
	})

	// @feature query.filter-relative-date
	it('hands back a span it cannot read, so a typed day filters itself', () => {
		expect(resolveSpan('2026-08-10', ANCHOR)).toEqual([ANCHOR, ANCHOR])
	})
})

describe('the words a span is written in', () => {
	// @feature query.filter-relative-date
	it('names every unit it spans, singular or plural', () => {
		expect(SPAN_UNITS.map((unit) => unitOf(`${unit}s`))).toEqual([...SPAN_UNITS])
		expect(SPAN_UNITS.map((unit) => unitOf(unit))).toEqual([...SPAN_UNITS])
		expect(unitOf('fortnight')).toBeUndefined()
		expect(unitOf(undefined)).toBeUndefined()
	})

	// @feature query.filter-relative-date
	it('reads a span back as the row that wrote it', () => {
		expect(spanLabel('current day')).toBe('Today')
		expect(spanLabel('last 1 day')).toBe('Yesterday')
		expect(spanLabel('current quarter')).toBe('This quarter')
		expect(spanLabel('last 3 months')).toBe('Last 3 months')
		expect(spanLabel('next 1 week')).toBe('Next week')
		expect(spanLabel('month to date')).toBe('This month to date')
		expect(spanLabel('last 2 weeks (include current)')).toBe('Last 2 weeks (include current)')
	})

	// @feature query.filter-relative-date
	it('prints a span it cannot read as it stands', () => {
		expect(spanLabel('2026-08-10')).toBe('2026-08-10')
	})

	// @feature query.filter-relative-date
	it('holds a preset apart from a span only the relative stages can reopen', () => {
		expect(isPreset('current day')).toBe(true)
		expect(isPreset('last 7 days')).toBe(true)
		expect(isPreset('last 3 months')).toBe(false)
	})
})

describe('the operator table', () => {
	// @feature query.filter-operators-by-type
	it('answers only for the kind that offers the operator', () => {
		expect(operatorOf('text', 'in')?.word).toBe('is')
		expect(operatorOf('date', '>')?.word).toBe('after')
		expect(operatorOf('number', '>')?.word).toBe('greater than')
		// no kind's table holds every operator
		expect(operatorOf('number', 'in')).toBeUndefined()
		expect(operatorOf('text', 'within')).toBeUndefined()
	})
})

describe('what a host sends', () => {
	// @feature query.filter
	it('sends the column by name, and the rule as it stands', () => {
		const column: QueryResultColumn = { name: 'posting_date', type: 'Date' }
		expect(
			toFilterArgs({ column, operator: 'within', value: { span: 'last 3 months' } }),
		).toEqual({
			column: { type: 'column', column_name: 'posting_date' },
			operator: 'within',
			value: { span: 'last 3 months' },
		})
	})
})

describe('the numbers a number filter offers', () => {
	// @feature query.filter-number-range
	it('cuts them from the column, not from a fixed list', () => {
		expect(numberQuickValues([0, 100])).toEqual([25, 50, 75])
		// a column of percentages gets cuts inside it, where 1,000 never was
		expect(numberQuickValues([0, 1])).toEqual([0.25, 0.5, 0.75])
	})

	// @feature query.filter-number-range
	it('offers nothing for a column it has no range for', () => {
		expect(numberQuickValues(undefined)).toEqual([])
		expect(numberQuickValues([5, 5])).toEqual([])
		expect(numberPairValues(undefined)).toEqual([])
	})

	// @feature query.filter-number-range
	it('offers the column in parts for a between stage', () => {
		expect(numberPairValues([0, 100])).toEqual([
			[0, 25],
			[25, 50],
			[50, 75],
			[75, 100],
		])
	})
})
