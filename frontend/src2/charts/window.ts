// The period a number card reads, as the picker writes it and as a label prints
// it.
//
// A period is written as a span or as a grain, never both. A span filters to a
// stretch of the calendar and groups by which stretch a row fell in. A grain
// filters nothing and groups by the grain. Both give one row per stretch with
// the newest last, which is why one comparison — the row before — serves both.
//
// One module owns the vocabulary. A span is a string the server's `get_window`
// parses, and nothing outside this file builds one — a span it cannot parse
// raises while the card runs, so the choices an author is offered and the
// strings they write have to be the same list.

import dayjs from 'dayjs'
import type { GranularityType } from '../helpers/constants'
import { getFormattedDate } from '../query/helpers'
import { __ } from '../translation'
import type { ChartConfig, NumberChartConfig, NumberComparison } from '../types/chart.types'
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

/**
 * How the card's period answers the question a period comparison asks, or
 * nothing when it cannot answer it.
 *
 * The comparison states the question — the period before this one, or the same
 * period a year back — and the period is what fetches it. A span reaches an
 * earlier period by shifting its own span, so it names the shift the engine has
 * to fetch beside the window. A grain filters nothing and already returns every
 * period it has, so the row before the last one is the answer and no shift is
 * needed. A year back is a span anchored a year earlier, which a grain cannot
 * name: it would have to count rows back, and a gap in the data would make it
 * count the wrong one.
 */
export function periodComparison(
	comparison: NumberComparison,
	period?: NumberPeriod,
): { shift?: WindowShift } | undefined {
	if (comparison.source === 'last year') {
		return period?.span ? { shift: { ...LAST_YEAR } } : undefined
	}
	if (comparison.source !== 'previous') return undefined

	const shift = previousWindowShift(period?.span)
	return shift ? { shift } : {}
}

// what a card offers, and what each choice writes

/** The period a card reads. One of `span` or `grain`, plus an optional anchor. */
export type NumberPeriod = NonNullable<NumberChartConfig['window']>

/** One entry of the picker. The value names a shape and a unit, never a count. */
export type WindowChoice = { label: string; value: string }

/** Marks the choices that write a grain rather than a span. */
const GRAIN = 'grain:'

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

/**
 * What the include-current toggle adds, worded as the choice that names it.
 *
 * "Include this month" is the option label `current:month` carries, so the
 * toggle names the exact period it extends the run over. A day has no "this
 * day" in English, and its option is called Today.
 */
export function includeCurrentLabel(unit: WindowUnit): string {
	if (unit === 'day') return __('Include today')
	return __('Include this {0}', windowUnitLabel(unit))
}

/**
 * What each choice is called. The key names the shape and the unit, which is
 * what puts the choice under a heading and what writes its period.
 */
const CHOICE_COPY: Record<string, string> = {
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
	'grain:day': __('Latest day'),
	'grain:week': __('Latest week'),
	'grain:month': __('Latest month'),
	'grain:quarter': __('Latest quarter'),
	'grain:year': __('Latest year'),
	'grain:fiscal year': __('Latest fiscal year'),
}

/** A run of choices under one heading, as the picker's Combobox reads them. */
export type WindowChoiceGroup = { group: string; hideLabel?: boolean; options: WindowChoice[] }

/**
 * The heading each shape sits under, in the order the picker lists them.
 *
 * Derived from the choice key rather than stored on each entry: the key already
 * names the shape, and a second copy of it would be one more thing to keep in
 * step.
 */
const CHOICE_GROUPS: { shape: string; group: string }[] = [
	{ shape: 'to date', group: __('Up to today') },
	{ shape: 'current', group: __('Whole current period') },
	{ shape: 'last', group: __('Previous periods') },
	{ shape: 'grain', group: __('Latest in the data') },
]

export function windowChoices(): WindowChoice[] {
	return Object.entries(CHOICE_COPY).map(([value, label]) => ({ value, label }))
}

/**
 * The picker's entries under their headings.
 *
 * Every choice `windowChoices` lists lands in exactly one group, which a test
 * holds to — a family added to the copy and left out here would be unpickable.
 */
export function windowChoiceGroups(): WindowChoiceGroup[] {
	const flat = windowChoices()

	return CHOICE_GROUPS.map(({ shape, group }) => ({
		group,
		options: flat.filter((choice) => choice.value.startsWith(`${shape}:`)),
	})).filter((entry) => entry.options.length)
}

/**
 * The period a card reads, from whichever shape wrote it.
 *
 * Before this field existed, a granularity on the date column grouped the card
 * and it read the newest bucket. Nothing writes that now, so the grain is
 * lifted here rather than branched on everywhere downstream.
 */
export function periodOf(config: NumberChartConfig): NumberPeriod | undefined {
	if (config.window?.span || config.window?.grain) return config.window

	const grain = config.date_column?.granularity
	return grain ? { grain } : undefined
}

/**
 * The choice a period was written by, or the period itself when nothing here
 * wrote it. Empty when the card reads no period, which the picker shows as its
 * placeholder — there is no "None" to pick, because a date column that groups
 * nothing is a date column doing nothing.
 */
export function choiceOfPeriod(period?: NumberPeriod): string {
	if (period?.grain) {
		const choice = `${GRAIN}${grainUnit(period.grain)}`
		return choice in CHOICE_COPY ? choice : period.grain
	}

	const parsed = parseWindowSpan(period?.span)
	if (!parsed) return period?.span || ''

	const choice = `${parsed.shape}:${parsed.unit}`
	return choice in CHOICE_COPY ? choice : period?.span || ''
}

/** What a date column gets when an author picks one. */
export const DEFAULT_CHOICE = 'to date:month'

/**
 * The period a choice writes, over the run length the author already set.
 *
 * Built whole rather than merged, so switching between the two families cannot
 * leave the old family's key behind — a period carrying both would group twice.
 */
export function periodOfChoice(choice: string, current?: NumberPeriod): NumberPeriod | undefined {
	if (!choice) return undefined

	if (choice.startsWith(GRAIN)) {
		const unit = choice.slice(GRAIN.length) as WindowUnit
		return { grain: WINDOW_GRAINS[unit] || (unit as GranularityType) }
	}

	// A choice nobody here wrote is a span, hand-authored or from a later
	// release, and it stands as it is.
	if (!(choice in CHOICE_COPY)) return { span: choice }

	const [shape, unit] = choice.split(':') as [WindowShape, WindowUnit]
	const previous = parseWindowSpan(current?.span)
	return {
		span: buildWindowSpan({
			shape,
			unit,
			count: previous?.count || 3,
			...(previous?.includeCurrent ? { includeCurrent: true } : {}),
		}),
	}
}

/** The window unit a grain names, for reading a grain period back off a choice. */
function grainUnit(grain: GranularityType): string {
	const unit = WINDOW_UNITS.find((candidate) => WINDOW_GRAINS[candidate] === grain)
	return unit || grain
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
