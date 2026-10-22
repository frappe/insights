import { describe, expect, it } from 'vitest'
import type { QueryResultColumn } from '../../types/query.types'
import {
	SPAN_UNITS,
	isPreset,
	numberPairValues,
	numberQuickValues,
	operatorOf,
	parsePeriod,
	periodLabel,
	periodStart,
	selectedRowKey,
	summaryParts,
	spanLabel,
	toFilterArgs,
	unitOf,
} from './filter_picker'

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
	it('answers only for the kind that lists the operator', () => {
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

describe('the numbers a number filter lists', () => {
	// @feature query.filter-number-range
	it('cuts them from the column, not from a fixed list', () => {
		expect(numberQuickValues([0, 100])).toEqual([25, 50, 75])
		// a column of percentages gets cuts inside it, where 1,000 never was
		expect(numberQuickValues([0, 1])).toEqual([0.25, 0.5, 0.75])
	})

	// @feature query.filter-number-range
	it('lists nothing for a column it has no range for', () => {
		expect(numberQuickValues(undefined)).toEqual([])
		expect(numberQuickValues([5, 5])).toEqual([])
		expect(numberPairValues(undefined)).toEqual([])
	})

	// @feature query.filter-number-range
	it('lists the column in parts for a between stage', () => {
		expect(numberPairValues([0, 100])).toEqual([
			[0, 25],
			[25, 50],
			[50, 75],
			[75, 100],
		])
	})
})

describe('the row a reopened rule marks', () => {
	const posted: QueryResultColumn = { name: 'posting_date', type: 'Date' }
	const status: QueryResultColumn = { name: 'status', type: 'String' }

	// A rule an older control wrote as `=` over a list reopens as `is`, so that is
	// the operator row it marks.
	// @feature query.reopen-operation
	it('marks the operator the rule reopens as', () => {
		expect(selectedRowKey({ column: status, operator: '=', value: ['Open'] }, 'operator')).toBe(
			'in',
		)
	})

	// @feature query.filter-relative-date
	it('marks the preset or the unit a span was picked from, and nothing for a shifted span', () => {
		const within = (value: any) => ({ column: posted, operator: 'within' as const, value })
		expect(selectedRowKey(within({ span: 'last 7 days' }), 'value')).toBe('span:last 7 days')
		expect(selectedRowKey(within(['last', '26', 'weeks']), 'unit')).toBe('span:last 26 weeks')
		// the picker stores "3 months ago" as the current month from a shifted anchor
		expect(
			selectedRowKey(within({ span: 'current month', anchor: '2026-05-10' }), 'value'),
		).toBeUndefined()
	})
})

// The site's fiscal year starts on 1 April here, the session's own default.
describe('the periods a date filter lists', () => {
	const posted: QueryResultColumn = { name: 'posting_date', type: 'Date' }
	const labels: Array<[any, string, string]> = [
		['year', '2025-01-01', '2025'],
		['fiscal year', '2025-04-01', 'FY 2025-26'],
		['quarter', '2025-07-01', 'Q3 2025'],
		['fiscal quarter', '2025-07-01', 'Q2 FY25-26'],
		['month', '2025-09-01', 'Sep 2025'],
	]

	// @feature dashboard.filter-date-periods
	it('names a period by its own label, and reads that label back', () => {
		for (const [unit, start, label] of labels) {
			expect(periodLabel(unit, start)).toBe(label)
			expect(parsePeriod(label.toLowerCase())).toEqual({ unit, start })
		}
		expect(parsePeriod('september 2025')).toEqual({ unit: 'month', start: '2025-09-01' })
		expect(parsePeriod('last 3 months')).toBeUndefined()
	})

	// @feature query.fiscal-quarter
	it('starts a fiscal period from the fiscal year start, in the calendar year before when it must', () => {
		expect(periodStart('fiscal quarter', '2026-01-15')).toBe('2026-01-01')
		expect(periodStart('fiscal quarter', '2025-05-20')).toBe('2025-04-01')
		expect(periodStart('fiscal year', '2026-01-15')).toBe('2025-04-01')
		expect(periodStart('quarter', '2025-05-20')).toBe('2025-04-01')
	})

	// @feature dashboard.filter-date-periods
	it('prints a picked period on the trigger, and reopens on its row', () => {
		const picked = {
			column: posted,
			operator: 'within' as const,
			value: { span: 'current fiscal quarter', anchor: '2025-07-01' },
		}
		expect(summaryParts(picked).value).toBe('Q2 FY25-26')
		expect(selectedRowKey(picked, 'quarter')).toBe('period:fiscal quarter:2025-07-01')
	})

	// @feature query.filter-relative-date-shift
	it('reads "3 months ago" as the month it lands in', () => {
		const value = { span: 'current month', anchor: '2026-05-10' }
		expect(summaryParts({ column: posted, operator: 'within', value }).value).toBe('May 2026')
	})
})
