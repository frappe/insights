// The vocabulary the filter picker speaks: the kinds a column falls in, the
// operator table each kind offers, the spans a date filter is written in, the
// one date formatter every stage prints through, and the parts of the line an
// overview row prints.

import { Calendar, Hash, Type } from 'lucide-vue-next'
import type { Component } from 'vue'
import { FIELDTYPES } from '../../helpers/constants'
import type { ManipulateType } from 'dayjs'
import dayjs from '../../helpers/dayjs'
import { column, filter_group } from '../../query/helpers'
import { __ } from '../../translation'
import type {
	ColumnDataType,
	FilterArgs,
	FilterGroup,
	FilterOperator,
	FilterValue,
	QueryResultColumn,
	Timespan,
} from '../../types/query.types'

/** One rule the picker holds. Hosts key a list of these by index. */
export type Filter = {
	column: QueryResultColumn
	operator: FilterOperator
	value: FilterValue
}

export type FilterKind = 'text' | 'number' | 'date'

export function kindOf(type: ColumnDataType): FilterKind {
	if (FIELDTYPES.NUMBER.includes(type)) return 'number'
	if (FIELDTYPES.DATE.includes(type)) return 'date'
	return 'text'
}

export function columnIcon(column: QueryResultColumn): Component {
	const kind = kindOf(column.type)
	if (kind === 'number') return Hash
	if (kind === 'date') return Calendar
	return Type
}

// --- operators -------------------------------------------------------------

/** An operator is a sign wherever one exists, and the word it is read as. */
export type OperatorDef = {
	sign: string
	word: string
	operator: FilterOperator
	needsValue: boolean
}

export const OPERATORS: Record<FilterKind, OperatorDef[]> = {
	text: [
		{ sign: __('is'), word: __('is'), operator: 'in', needsValue: true },
		{ sign: __('is not'), word: __('is not'), operator: 'not_in', needsValue: true },
		{ sign: '=', word: __('equals'), operator: '=', needsValue: true },
		{ sign: '≠', word: __('not equals'), operator: '!=', needsValue: true },
		{ sign: __('contains'), word: __('contains'), operator: 'contains', needsValue: true },
		{
			sign: __('does not contain'),
			word: __('does not contain'),
			operator: 'not_contains',
			needsValue: true,
		},
		{
			sign: __('starts with'),
			word: __('starts with'),
			operator: 'starts_with',
			needsValue: true,
		},
		{ sign: __('ends with'), word: __('ends with'), operator: 'ends_with', needsValue: true },
		{ sign: __('is set'), word: __('is set'), operator: 'is_set', needsValue: false },
		{
			sign: __('is not set'),
			word: __('is not set'),
			operator: 'is_not_set',
			needsValue: false,
		},
	],
	number: [
		{ sign: '=', word: __('equals'), operator: '=', needsValue: true },
		{ sign: '≠', word: __('not equals'), operator: '!=', needsValue: true },
		{ sign: '>', word: __('greater than'), operator: '>', needsValue: true },
		{ sign: '≥', word: __('greater than or equals'), operator: '>=', needsValue: true },
		{ sign: '<', word: __('less than'), operator: '<', needsValue: true },
		{ sign: '≤', word: __('less than or equals'), operator: '<=', needsValue: true },
		{ sign: __('between'), word: __('between'), operator: 'between', needsValue: true },
	],
	date: [
		{ sign: __('between'), word: __('between'), operator: 'between', needsValue: true },
		{ sign: __('within'), word: __('within'), operator: 'within', needsValue: true },
		{ sign: '=', word: __('equals'), operator: '=', needsValue: true },
		{ sign: '≠', word: __('not equals'), operator: '!=', needsValue: true },
		{ sign: '>', word: __('after'), operator: '>', needsValue: true },
		{ sign: '≥', word: __('on or after'), operator: '>=', needsValue: true },
		{ sign: '<', word: __('before'), operator: '<', needsValue: true },
		{ sign: '≤', word: __('on or before'), operator: '<=', needsValue: true },
	],
}

export function operatorOf(kind: FilterKind, operator: FilterOperator): OperatorDef {
	return OPERATORS[kind].find((op) => op.operator === operator)!
}

export function defaultOperator(kind: FilterKind): OperatorDef {
	const operator: FilterOperator = kind === 'text' ? 'in' : kind === 'number' ? '>=' : 'between'
	return operatorOf(kind, operator)
}

/** The kind's operators, its default first. */
export function operatorRows(kind: FilterKind): OperatorDef[] {
	const first = defaultOperator(kind)
	return [first, ...OPERATORS[kind].filter((op) => op !== first)]
}

/** `is` and `is not` over text are a multi-select over the distinct values. */
export function isMulti(kind: FilterKind, op?: OperatorDef): boolean {
	return kind === 'text' && (op?.operator === 'in' || op?.operator === 'not_in')
}

/** The `operator value` pair a text multi-select commits: always a list. */
export function textRule(
	op: OperatorDef,
	picked: string[],
): { operator: FilterOperator; value: FilterValue } {
	return { operator: op.operator, value: [...picked] }
}

// --- stages ----------------------------------------------------------------

/**
 * Where the path stands. The three date stages after `within` are stages of
 * their own, so the keyboard reaches a relative span the way it reaches
 * everything else.
 */
export type Stage = 'overview' | 'column' | 'operator' | 'value' | 'relative' | 'unit'

/** One row of a stage's list. */
export type ListItem = {
	key: string
	label: string
	icon?: Component
	/** a Checkbox before the label */
	checked?: boolean
	/** reka owns this row's tick, through its own model */
	tick?: boolean
	/** dim text after the label */
	note?: string
	/** overview rows: the sign and the value, typed apart from the label */
	operator?: string
	value?: string
	/** a ghost × at the end of the row */
	removable?: boolean
	/** a divider above the row */
	separated?: boolean
	filter?: Filter
}

// --- numbers ---------------------------------------------------------------

export const NUMBER_QUICK = [100, 500, 1_000, 5_000]
export const NUMBER_PAIRS: Array<[number, number]> = [
	[0, 1_000],
	[1_000, 5_000],
	[5_000, 10_000],
]

export function formatNumber(raw: any): string {
	const value = Number(raw)
	return Number.isFinite(value) ? value.toLocaleString('en-US') : String(raw ?? '')
}

export function parseNumber(text: string): number | undefined {
	const cleaned = text.trim().replace(/,/g, '')
	if (!cleaned) return undefined
	const value = Number(cleaned)
	return Number.isFinite(value) ? value : undefined
}

/** "a to b", "a - b", "a-b", or "a b" */
export function splitPair(text: string): [string, string] | undefined {
	const t = text.trim()
	const at = t.search(/\s+to\s+/) >= 0 ? t.search(/\s+to\s+/) : t.search(/\s+-\s+/)
	if (at >= 0) {
		const width = t.slice(at).match(/^\s+(to|-)\s+/)![0].length
		return [t.slice(0, at), t.slice(at + width)]
	}
	const dashes = t.split('-').length - 1
	if (dashes === 1 && /^\d/.test(t)) {
		const [a, b] = t.split('-')
		return [a.trim(), b.trim()]
	}
	const words = t.split(/\s+/)
	if (words.length === 2) return [words[0], words[1]]
	return undefined
}

/** What a number rule reads as, wherever the picker prints one. */
export function numberPreview(op: OperatorDef, value: number | [number, number]): string {
	if (Array.isArray(value))
		return __('between {0} and {1}', formatNumber(value[0]), formatNumber(value[1]))
	return `${op.sign} ${formatNumber(value)}`
}

// --- spans -----------------------------------------------------------------

export const DATE_FORMAT = 'YYYY-MM-DD'

export const SPAN_UNITS = ['day', 'week', 'month', 'quarter', 'year'] as const
export type SpanUnit = (typeof SPAN_UNITS)[number]

const UNIT_WORDS: Record<SpanUnit, [string, string]> = {
	day: [__('day'), __('days')],
	week: [__('week'), __('weeks')],
	month: [__('month'), __('months')],
	quarter: [__('quarter'), __('quarters')],
	year: [__('year'), __('years')],
}

/** The unit a typed word names. Typing stays in English, as the spans are. */
export function unitOf(word?: string): SpanUnit | undefined {
	return SPAN_UNITS.find((unit) => unit === word?.replace(/s$/, ''))
}

function unitWords(unit: SpanUnit, count: number): string {
	const [one, many] = UNIT_WORDS[unit]
	return count === 1 ? one : `${count} ${many}`
}

/**
 * The span a `within` value names, whatever shape it was written in. The old
 * date control wrote the words of a span as a list or as a string; the picker
 * writes `{ span }`. The server reads all three through `read_timespan`, so the
 * picker does too.
 */
export function timespanOf(value: FilterValue): Timespan | undefined {
	const clean = (span: string) => span.trim().toLowerCase().replace(/\s+/g, ' ')

	if (Array.isArray(value)) {
		const span = clean(value.filter((word) => word != null && word !== '').join(' '))
		return span ? { span } : undefined
	}
	if (typeof value === 'string') {
		const span = clean(value)
		return span ? { span } : undefined
	}
	if (value && typeof value === 'object' && typeof (value as Timespan).span === 'string') {
		const timespan = value as Timespan
		const span = clean(timespan.span)
		return span ? { ...timespan, span } : undefined
	}
	return undefined
}

export type SpanDirection = 'last' | 'next' | 'current'

export type RelativeForm = {
	direction: SpanDirection
	count: number
	unit: SpanUnit
	includeCurrent: boolean
}

/**
 * The presets the `within` stage offers. Every span here is one
 * `charts/window.ts` writes and the server's `get_window` parses — a "last N"
 * span covers whole periods behind today, so "Last 7 days" ends yesterday.
 */
export const DATE_PRESETS: Array<{ label: string; span: string }> = [
	{ label: __('Today'), span: 'current day' },
	{ label: __('Yesterday'), span: 'last 1 day' },
	{ label: __('Last 7 days'), span: 'last 7 days' },
	{ label: __('Last 30 days'), span: 'last 30 days' },
	{ label: __('This month'), span: 'current month' },
	{ label: __('Last month'), span: 'last 1 month' },
	{ label: __('This quarter'), span: 'current quarter' },
	{ label: __('This year'), span: 'current year' },
]

export function isPreset(span: string): boolean {
	return DATE_PRESETS.some((p) => p.span === span)
}

/** The span a relative form is written as. */
export function spanOf(form: RelativeForm): string {
	if (form.direction === 'current') return `current ${form.unit}`
	const unit = form.count === 1 ? form.unit : `${form.unit}s`
	const base = `${form.direction} ${form.count} ${unit}`
	return form.includeCurrent ? `${base} (include current)` : base
}

/** The form behind a span, where the span is a relative one. */
export function formOf(span: string): RelativeForm | null {
	const includeCurrent = /\(include current\)$/.test(span)
	const words = span
		.replace(/\s*\(include current\)\s*$/, '')
		.trim()
		.toLowerCase()
		.split(/\s+/)
	if (words[0] === 'current') {
		const unit = unitOf(words[1])
		return unit ? { direction: 'current', count: 1, unit, includeCurrent: false } : null
	}
	if (words[0] !== 'last' && words[0] !== 'next') return null
	const count = Number(words[1])
	const unit = unitOf(words[2])
	if (!Number.isFinite(count) || !unit) return null
	return { direction: words[0], count, unit, includeCurrent }
}

/** The unit a `<unit> to date` span names: the period so far, up to the anchor. */
function toDateUnit(span: string): SpanUnit | undefined {
	const match = span
		.trim()
		.toLowerCase()
		.match(/^(\S+) to date$/)
	return match ? unitOf(match[1]) : undefined
}

/** `get_window` in dayjs, for the range the calendar and the notes print. */
export function resolveSpan(span: string, anchor?: string): [string, string] {
	const today = anchor ? dayjs(anchor) : dayjs()

	const toDate = toDateUnit(span)
	if (toDate)
		return [
			today.startOf(toDate as ManipulateType).format(DATE_FORMAT),
			today.format(DATE_FORMAT),
		]

	const form = formOf(span)
	if (!form) return [span, span]

	// dayjs types `quarter` only through the plugin helpers/dayjs loads.
	const unit = form.unit as ManipulateType
	const currentStart = today.startOf(unit)

	if (form.direction === 'current')
		return [currentStart.format(DATE_FORMAT), today.endOf(unit).format(DATE_FORMAT)]

	if (form.direction === 'last') {
		// N whole periods, the last of them ending the day before the current
		// one starts, unless the current one is asked for too.
		const from = currentStart.subtract(form.count, unit)
		const to = form.includeCurrent ? today.endOf(unit) : currentStart.subtract(1, 'day')
		return [from.format(DATE_FORMAT), to.format(DATE_FORMAT)]
	}

	const nextStart = currentStart.add(1, unit)
	const from = form.includeCurrent ? currentStart : nextStart
	const to = nextStart.add(form.count, unit).subtract(1, 'day')
	return [from.format(DATE_FORMAT), to.format(DATE_FORMAT)]
}

/** A span in the picker's words: `Today`, `Last 7 days`, `Next 2 weeks`. */
export function spanLabel(span: string): string {
	const preset = DATE_PRESETS.find((p) => p.span === span)
	if (preset) return preset.label

	const toDate = toDateUnit(span)
	if (toDate) return __('This {0} to date', UNIT_WORDS[toDate][0])

	const form = formOf(span)
	if (!form) return span
	if (form.direction === 'current') return __('This {0}', UNIT_WORDS[form.unit][0])

	const phrase = unitWords(form.unit, form.count)
	const label = form.direction === 'last' ? __('Last {0}', phrase) : __('Next {0}', phrase)
	return form.includeCurrent ? `${label} ${__('(include current)')}` : label
}

/** A span as the days it covers, through the one date formatter. */
export function spanDates(value: FilterValue, anchor?: string): string {
	const timespan = timespanOf(value)
	if (!timespan) return ''
	const [from, to] = resolveSpan(timespan.span, anchor || timespan.anchor)
	return formatDate(from, to)
}

/** The directions the `Relative…` row opens onto. */
export const RELATIVE_DIRECTIONS: Array<{ key: SpanDirection; label: string }> = [
	{ key: 'last', label: __('Last') },
	{ key: 'next', label: __('Next') },
	{ key: 'current', label: __('This') },
]

/** The unit rows the last stage of a relative span lists, the count folded in. */
export function unitRows(form: RelativeForm): Array<{ label: string; span: string }> {
	return SPAN_UNITS.map((unit) => ({
		label: form.direction === 'current' ? UNIT_WORDS[unit][0] : unitWords(unit, form.count),
		span: spanOf({ ...form, unit }),
	}))
}

/** The one row the `within` stage carries past its presets. */
export const RELATIVE_ROW = { key: 'relative', label: __('Relative…') }

/** The calendar an operator's value stage opens under the list. */
export function calendarOf(op: OperatorDef): 'range' | 'day' | undefined {
	if (op.operator === 'within') return undefined
	return op.operator === 'between' ? 'range' : 'day'
}

/** "last 3 months", "this quarter", "next 2 weeks" → the span the server parses */
export function parseSpan(text: string): string | undefined {
	const preset = DATE_PRESETS.find((p) => p.label.toLowerCase() === text.trim().toLowerCase())
	if (preset) return preset.span
	const words = text.trim().toLowerCase().split(/\s+/)
	if (words[0] === 'today') return 'current day'
	if (words[0] === 'yesterday') return 'last 1 day'
	const head = words[0] === 'this' ? 'current' : words[0]
	if (!['current', 'last', 'next'].includes(head)) return undefined
	const hasCount = /^\d+$/.test(words[1] || '')
	const count = hasCount ? Number(words[1]) : 1
	const unit = unitOf(hasCount ? words[2] : words[1])
	if (!unit) return undefined
	if (head === 'current') return `current ${unit}`
	return `${head} ${count} ${unit}${count === 1 ? '' : 's'}`
}

// --- dates -----------------------------------------------------------------

/**
 * The one date formatter the picker prints through. A single day reads
 * `11 Sep 2026`; a range drops whatever repeats between its two ends —
 * `5 – 11 Sep 2026`, `5 Sep – 11 Sep 2026`, `21 Mar 2023 – 11 Sep 2026`.
 */
export function formatDate(from: string, to?: string): string {
	const start = dayjs(from)
	if (!start.isValid()) return from ?? ''
	if (!to || to === from) return start.format('D MMM YYYY')

	const end = dayjs(to)
	if (!end.isValid()) return `${start.format('D MMM YYYY')} – ${to}`
	if (start.year() !== end.year())
		return `${start.format('D MMM YYYY')} – ${end.format('D MMM YYYY')}`
	if (start.month() === end.month()) return `${start.format('D')} – ${end.format('D MMM YYYY')}`
	return `${start.format('D MMM')} – ${end.format('D MMM YYYY')}`
}

export type ParsedDate = { operator: FilterOperator; value: FilterValue }

const DAY = /^\d{4}-\d{2}-\d{2}$/

function isDay(text: string): boolean {
	return DAY.test(text) && dayjs(text).isValid()
}

/** What a typed date phrase means, where the value stage takes one. */
export function parseDatePhrase(raw: string): ParsedDate | null {
	const text = raw.trim().toLowerCase().replace(/\s+/g, ' ')
	if (!text) return null

	const preset = DATE_PRESETS.find((p) => p.label.toLowerCase() === text)
	if (preset) return { operator: 'within', value: { span: preset.span } }

	let match = text.match(/^(last|next) (\d+) ([a-z]+)$/)
	if (match) {
		const unit = unitOf(match[3])
		if (!unit) return null
		const form: RelativeForm = {
			direction: match[1] as SpanDirection,
			count: Number(match[2]),
			unit,
			includeCurrent: false,
		}
		return { operator: 'within', value: { span: spanOf(form) } }
	}

	match = text.match(/^(this|current) ([a-z]+)$/)
	if (match) {
		const unit = unitOf(match[2])
		return unit ? { operator: 'within', value: { span: `current ${unit}` } } : null
	}

	match = text.match(/^(\d+) ([a-z]+) ago$/)
	if (match) {
		const unit = unitOf(match[2])
		if (!unit) return null
		const anchor = dayjs()
			.subtract(Number(match[1]), unit as ManipulateType)
			.format(DATE_FORMAT)
		return { operator: 'within', value: { span: `current ${unit}`, anchor } }
	}

	match = text.match(/^(\S+) to (\S+)$/)
	if (match && isDay(match[1]) && isDay(match[2])) {
		const [a, b] = [match[1], match[2]].sort()
		return { operator: 'between', value: [a, b] }
	}

	match = text.match(/^(before|after) (\S+)$/)
	if (match && isDay(match[2])) {
		return { operator: match[1] === 'before' ? '<' : '>', value: match[2] }
	}

	if (isDay(text)) return { operator: '=', value: text }
	return null
}

/**
 * The days the calendar highlights, read off the input. A range keeps its start
 * while the second day is still unwritten, so a first click stands.
 */
export function calendarValue(mode: 'range' | 'day', text: string): string | [string, string] {
	const clean = text.trim()
	if (mode === 'day') return isDay(clean) ? clean : ''
	const match = clean.match(/^(\S+)(?:\s+to(?:\s+(\S+))?)?$/)
	if (!match || !isDay(match[1])) return ['', '']
	const end = match[2] || ''
	return [match[1], isDay(end) ? end : '']
}

/** What a calendar click writes into the input. */
export function calendarText(value: string | string[] | undefined): string {
	if (!Array.isArray(value)) return value || ''
	const [from, to] = value
	if (!from) return ''
	return to ? `${from} to ${to}` : `${from} to `
}

// --- the overview row ------------------------------------------------------

function listSummary(value: FilterValue): string {
	const values = (Array.isArray(value) ? value : [value]).filter((v) => v != null && v !== '')
	const shown = values.slice(0, 2).join(', ')
	const rest = values.length - 2
	return rest > 0 ? `${shown} +${rest}` : shown
}

/**
 * The parts of an overview row: the column it filters, the sign it filters by,
 * the word that sign is read as, and the value it filters to. The row types
 * them apart, so they never merge into a sentence. A host that has no room for
 * a sign column — the dashboard widget — prints the word instead.
 */
export function summaryParts(filter: Filter): {
	label: string
	operator: string
	word: string
	value: string
} {
	const kind = kindOf(filter.column.type)
	return {
		label: filter.column.name,
		operator: operatorSign(filter.operator),
		word: operatorWord(kind, filter.operator),
		value: valueSummary(filter),
	}
}

/** The word a committed operator is read as, in the kind's own vocabulary. */
function operatorWord(kind: FilterKind, operator: FilterOperator): string {
	const def = OPERATORS[kind].find((op) => op.operator === operator)
	return def?.word || operatorSign(operator)
}

/** The sign a committed operator prints as. `in` and `not_in` have none, so
 * they print their word where the other operators print a sign. */
function operatorSign(operator: FilterOperator): string {
	const signs: Record<string, string> = {
		in: __('is'),
		not_in: __('is not'),
		'=': '=',
		'!=': '≠',
		'>': '>',
		'>=': '≥',
		'<': '<',
		'<=': '≤',
		between: __('between'),
		within: __('within'),
		contains: __('contains'),
		not_contains: __('does not contain'),
		starts_with: __('starts with'),
		ends_with: __('ends with'),
		is_set: __('is set'),
		is_not_set: __('is not set'),
	}
	return signs[operator] || String(operator)
}

function valueSummary(filter: Filter): string {
	const { operator, value } = filter

	if (operator === 'is_set' || operator === 'is_not_set') return ''
	if (operator === 'in' || operator === 'not_in') return listSummary(value)
	// `=` and `!=` over a list is how an older text rule was written
	if (kindOf(filter.column.type) === 'text' && Array.isArray(value)) return listSummary(value)

	if (kindOf(filter.column.type) === 'date') {
		if (operator === 'within') {
			const timespan = timespanOf(value)
			if (!timespan) return ''
			if (timespan.anchor && timespan.span === 'current day')
				return formatDate(timespan.anchor)
			return spanLabel(timespan.span)
		}
		if (operator === 'between') {
			const [from, to] = (value as string[]) || []
			return formatDate(from, to)
		}
		return formatDate(String(value))
	}

	if (operator === 'between') {
		const [from, to] = (value as any[]) || []
		return __('{0} and {1}', formatNumber(from), formatNumber(to))
	}
	if (kindOf(filter.column.type) === 'number') return formatNumber(value)

	return String(value ?? '')
}

// --- a rule, back onto the path -------------------------------------------

export type Path = {
	column: QueryResultColumn
	op: OperatorDef
	/** text `is` / `is not` */
	picked: string[]
	/** what the input reads: a value, a number, a date phrase, or a relative count */
	text: string
	/** a `within` rule that is not a preset reopens on the relative stages */
	relative?: RelativeForm
}

export function pathOf(filter: Filter): Path {
	const kind = kindOf(filter.column.type)
	const { operator, value } = filter
	const base: Path = {
		column: filter.column,
		op: defaultOperator(kind),
		picked: [],
		text: '',
	}

	if (kind === 'text') {
		// an older rule wrote a list as `=` / `!=`; it reopens as `is` / `is not`
		const list = Array.isArray(value)
		if (
			operator === 'in' ||
			operator === 'not_in' ||
			(list && (operator === '=' || operator === '!='))
		) {
			const multi = operator === 'in' || operator === '=' ? 'in' : 'not_in'
			return {
				...base,
				op: operatorOf('text', multi),
				picked: ((value as string[]) || []).map(String),
			}
		}
		const op = operatorOf('text', operator) || base.op
		return { ...base, op, text: op.needsValue ? String(value ?? '') : '' }
	}

	if (kind === 'number') {
		const op = operatorOf('number', operator) || base.op
		if (operator === 'between') {
			const [from, to] = (value as number[]) || []
			return { ...base, op, text: `${from} to ${to}` }
		}
		return { ...base, op, text: String(value ?? '') }
	}

	if (operator === 'within') {
		const span = timespanOf(value)?.span || ''
		const relative = isPreset(span) ? undefined : formOf(span) || undefined
		return {
			...base,
			op: operatorOf('date', 'within'),
			relative,
			text: relative && relative.direction !== 'current' ? String(relative.count) : '',
		}
	}
	if (operator === 'between') {
		const [from, to] = (value as string[]) || []
		return {
			...base,
			op: operatorOf('date', 'between'),
			text: from && to ? `${from} to ${to}` : '',
		}
	}
	const op = operatorOf('date', operator) || base.op
	return { ...base, op, text: String(value ?? '') }
}

// --- what a host sends -----------------------------------------------------

export function toFilterArgs(filter: Filter): FilterArgs {
	return {
		column: column(filter.column.name),
		operator: filter.operator,
		value: filter.value,
	}
}

export function toFilterGroup(filters: Filter[]): FilterGroup {
	return filter_group({
		logical_operator: 'And',
		filters: filters.map(toFilterArgs),
	})
}
