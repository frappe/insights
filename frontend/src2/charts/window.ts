// The period a number card reads, as the picker writes it and as a label prints
// it.
//
// One module owns the vocabulary. A span is a string the server's `get_window`
// parses, and nothing outside this file builds one — a span it cannot parse
// raises while the card runs, so the choices an author is offered and the
// strings they write have to be the same list.

import dayjs from 'dayjs'
import type { GranularityType } from '../helpers/constants'
import { getFormattedDate } from '../query/helpers'
import { __ } from '../translation'
import type { ChartConfig, NumberChartConfig } from '../types/chart.types'
import type { QueryResultRow } from '../types/query.types'

export const WINDOW_UNITS = ['day', 'week', 'month', 'quarter', 'year', 'fiscal year'] as const
export type WindowUnit = (typeof WINDOW_UNITS)[number]

/**
 * The three spans the server reads: the period so far, the whole period, and a
 * run of whole periods behind it.
 */
export type WindowShape = 'to date' | 'current' | 'last'

export type WindowSpan = {
	shape: WindowShape
	unit: WindowUnit
	/** How many whole periods a `last` span covers. `last` only. */
	count?: number
	/** Extends a `last` span over the period the card is read in. `last` only. */
	includeCurrent?: boolean
}

export type WindowShift = { unit: string; count: number }

/** The shift a flow metric is read against: the same span, one year back. */
export const LAST_YEAR: WindowShift = { unit: 'year', count: -1 }

export function buildWindowSpan(span: WindowSpan): string {
	if (span.shape === 'to date') return `${span.unit} to date`
	if (span.shape === 'current') return `current ${span.unit}`

	const count = Math.max(1, Math.round(span.count || 1))
	const unit = count === 1 ? span.unit : `${span.unit}s`
	return `last ${count} ${unit}${span.includeCurrent ? ' (include current)' : ''}`
}

export function parseWindowSpan(span?: string): WindowSpan | undefined {
	if (!span) return undefined

	let rest = span.trim().toLowerCase()
	const includeCurrent = rest.includes('(include current)')
	rest = rest.replace('(include current)', '').trim()

	if (rest.endsWith('to date')) {
		const unit = toUnit(rest.slice(0, -'to date'.length))
		return unit ? { shape: 'to date', unit } : undefined
	}

	if (rest.startsWith('current ')) {
		const unit = toUnit(rest.slice('current '.length))
		return unit ? { shape: 'current', unit } : undefined
	}

	if (rest.startsWith('last ')) {
		const words = rest.slice('last '.length).split(' ')
		const count = Number(words[0])
		const unit = toUnit(words.slice(1).join(' '))
		if (!unit || !count || count < 1) return undefined
		return { shape: 'last', unit, count, ...(includeCurrent ? { includeCurrent } : {}) }
	}

	return undefined
}

function toUnit(words: string): WindowUnit | undefined {
	const unit = words.trim().replace(/s$/, '') as WindowUnit
	return WINDOW_UNITS.includes(unit) ? unit : undefined
}

/** How many whole periods the span covers, which is what makes a window long. */
export function windowPeriods(span: WindowSpan): number {
	if (span.shape !== 'last') return 1
	return Math.max(1, Math.round(span.count || 1)) + (span.includeCurrent ? 1 : 0)
}

/**
 * The shift that names the window before this one: the same span, moved back by
 * its own length, so the two windows meet and never overlap.
 */
export function previousWindowShift(span?: string): WindowShift | undefined {
	const parsed = parseWindowSpan(span)
	if (!parsed) return undefined
	return { unit: parsed.unit, count: -windowPeriods(parsed) }
}

export function sameShift(one?: WindowShift, other?: WindowShift): boolean {
	if (!one || !other) return false
	return one.unit === other.unit && one.count === other.count
}

// what a card offers, and what each choice writes

/** One entry of the picker. The value names a shape and a unit, never a count. */
export type WindowChoice = { label: string; value: string }

export const NO_WINDOW = 'none'

const UNIT_LABELS: Record<WindowUnit, { one: string; many: string }> = {
	day: { one: __('day'), many: __('days') },
	week: { one: __('week'), many: __('weeks') },
	month: { one: __('month'), many: __('months') },
	quarter: { one: __('quarter'), many: __('quarters') },
	year: { one: __('year'), many: __('years') },
	'fiscal year': { one: __('fiscal year'), many: __('fiscal years') },
}

export function windowUnitLabel(unit: WindowUnit, many = false): string {
	const labels = UNIT_LABELS[unit]
	return many ? labels.many : labels.one
}

const CHOICE_LABELS: Record<string, string> = {
	'to date:week': __('Week to date'),
	'to date:month': __('Month to date'),
	'to date:quarter': __('Quarter to date'),
	'to date:year': __('Year to date'),
	'to date:fiscal year': __('Fiscal year to date'),
	'current:day': __('Today'),
	'current:week': __('This week'),
	'current:month': __('This month'),
	'current:quarter': __('This quarter'),
	'current:year': __('This year'),
	'current:fiscal year': __('This fiscal year'),
	'last:day': __('Last N days'),
	'last:week': __('Last N weeks'),
	'last:month': __('Last N months'),
	'last:quarter': __('Last N quarters'),
	'last:year': __('Last N years'),
	'last:fiscal year': __('Last N fiscal years'),
}

export function windowChoices(): WindowChoice[] {
	return [
		{ label: __('None'), value: NO_WINDOW },
		...Object.entries(CHOICE_LABELS).map(([value, label]) => ({ label, value })),
	]
}

/** The choice a span was written by, or the span itself when nothing here wrote it. */
export function windowChoiceOf(span?: string): string {
	const parsed = parseWindowSpan(span)
	if (!parsed) return span || NO_WINDOW

	const choice = `${parsed.shape}:${parsed.unit}`
	return choice in CHOICE_LABELS ? choice : span || NO_WINDOW
}

/** The span a choice writes, over the run length the author already set. */
export function spanOfChoice(choice: string, current?: string): string | undefined {
	if (choice === NO_WINDOW) return undefined
	if (!(choice in CHOICE_LABELS)) return choice

	const [shape, unit] = choice.split(':') as [WindowShape, WindowUnit]
	const previous = parseWindowSpan(current)
	return buildWindowSpan({
		shape,
		unit,
		count: previous?.count || 3,
		...(previous?.includeCurrent ? { includeCurrent: true } : {}),
	})
}

// how a window prints

const WINDOW_GRAINS: Record<WindowUnit, GranularityType> = {
	day: 'day',
	week: 'week',
	month: 'month',
	quarter: 'quarter',
	year: 'year',
	'fiscal year': 'fiscal_year',
}

/** One period of a unit, as dayjs steps it. */
const UNIT_STEPS: Record<WindowUnit, [number, 'day' | 'week' | 'month' | 'year']> = {
	day: [1, 'day'],
	week: [1, 'week'],
	month: [1, 'month'],
	quarter: [3, 'month'],
	year: [1, 'year'],
	'fiscal year': [1, 'year'],
}

/**
 * The period a window covers, from the date it starts on.
 *
 * A window is grouped by membership, so its dimension carries no granularity
 * and its start date prints raw. The span is what says how long the window is,
 * so the span is what names it — and a span of several periods is named by the
 * whole run, because the first period alone reads as that period's own number.
 */
export function formatWindowLabel(span: string, start: any): any {
	const parsed = parseWindowSpan(span)
	if (!parsed || !start) return start

	const grain = WINDOW_GRAINS[parsed.unit]
	const first = getFormattedDate(String(start), grain)

	const periods = windowPeriods(parsed)
	if (periods < 2) return first

	const [size, step] = UNIT_STEPS[parsed.unit]
	const last = dayjs(String(start)).add(size * (periods - 1), step)
	return `${first} – ${getFormattedDate(last.format('YYYY-MM-DD'), grain)}`
}

/**
 * The rows a card draws, with its window column read as a period rather than as
 * the date the period starts on.
 */
export function labelWindowRows(
	rows: QueryResultRow[],
	chart_type: string,
	config: ChartConfig,
): QueryResultRow[] {
	if (chart_type !== 'Number') return rows

	const number = config as NumberChartConfig
	const span = number.window?.span
	const column = number.date_column?.dimension_name || number.date_column?.column_name
	if (!span || !column) return rows

	return rows.map((row) =>
		column in row ? { ...row, [column]: formatWindowLabel(span, row[column]) } : row,
	)
}

/** What a shifted window is called, when the author did not word it themselves. */
export function windowShiftLabel(shift?: WindowShift): string | undefined {
	if (!shift?.count || !WINDOW_UNITS.includes(shift.unit as WindowUnit)) return undefined

	const away = Math.abs(shift.count)
	const worded = windowUnitLabel(shift.unit as WindowUnit, away > 1)

	if (shift.count < 0) {
		return away === 1
			? __('vs same period last {0}', worded)
			: __('vs same period {0} {1} ago', String(away), worded)
	}
	return away === 1
		? __('vs same period next {0}', worded)
		: __('vs same period {0} {1} ahead', String(away), worded)
}
