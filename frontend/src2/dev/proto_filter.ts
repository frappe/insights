// PROTOTYPE — throwaway. See docs/projects/table-experience/issues/01-filter-picker.md
//
// The vocabulary the picker speaks: kinds, date presets, and the two halves of
// the line an overview row prints. There is no operator vocabulary left — each
// type has exactly one picker, and the picker decides the operator.

import dayjs from 'dayjs'
import { Calendar, Hash, Type } from 'lucide-vue-next'
import type { Component } from 'vue'
import { FIELDTYPES } from '../helpers/constants'
import type {
	ColumnDataType,
	FilterOperator,
	FilterValue,
	QueryResultColumn,
	Timespan,
} from '../types/query.types'

export type ProtoKind = 'text' | 'number' | 'date'

export type ProtoFilter = {
	id: number
	column: QueryResultColumn
	operator: FilterOperator
	value: FilterValue
}

export function kindOf(type: ColumnDataType): ProtoKind {
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

// --- dates -----------------------------------------------------------------

export const DATE_FORMAT = 'YYYY-MM-DD'

/**
 * The presets the calendar's sidebar offers. Every span here is one
 * `charts/window.ts` writes and the server's `get_window` parses — a "last N"
 * span covers whole periods behind today, so "Last 7 days" ends yesterday.
 */
export const DATE_PRESETS: Array<{ label: string; span: string }> = [
	{ label: 'Today', span: 'current day' },
	{ label: 'Yesterday', span: 'last 1 day' },
	{ label: 'Last 7 days', span: 'last 7 days' },
	{ label: 'Last 30 days', span: 'last 30 days' },
	{ label: 'This month', span: 'current month' },
	{ label: 'Last month', span: 'last 1 month' },
	{ label: 'This quarter', span: 'current quarter' },
	{ label: 'This year', span: 'current year' },
]

/** The span a single calendar day writes: the day itself, as a window. */
export function daySpan(date: string): Timespan {
	return { span: 'current day', anchor: date }
}

export function isDaySpan(value: FilterValue): boolean {
	const span = value as Timespan
	return Boolean(span?.anchor && span.span === 'current day')
}

/** `get_window` in dayjs, for the range the calendar highlights. */
export function resolveSpan(span: string, anchor?: string): [string, string] {
	const today = anchor ? dayjs(anchor) : dayjs()
	const words = span.trim().toLowerCase().split(' ')

	if (words[0] === 'current') {
		const unit = words[1] as dayjs.ManipulateType
		return [today.startOf(unit).format(DATE_FORMAT), today.endOf(unit).format(DATE_FORMAT)]
	}

	// "last N days" — N whole periods, the last of them ending the day before
	// the current one starts.
	const count = Number(words[1]) || 1
	const unit = words[2].replace(/s$/, '') as dayjs.ManipulateType
	const currentStart = today.startOf(unit)
	return [
		currentStart.subtract(count, unit).format(DATE_FORMAT),
		currentStart.subtract(1, 'day').format(DATE_FORMAT),
	]
}

export function presetLabel(span: string): string {
	return DATE_PRESETS.find((preset) => preset.span === span)?.label || span
}

function formatDay(date: string): string {
	return dayjs(date).format('D MMM YYYY')
}

function formatRange(from: string, to: string): string {
	const start = dayjs(from)
	const end = dayjs(to)
	if (!start.isValid() || !end.isValid()) return `${from} – ${to}`
	const startText =
		start.year() === end.year() ? start.format('D MMM') : start.format('D MMM YYYY')
	return `${startText} – ${end.format('D MMM YYYY')}`
}

// --- the overview row ------------------------------------------------------

function formatNumber(raw: any): string {
	const value = Number(raw)
	return Number.isFinite(value) ? value.toLocaleString('en-US') : String(raw ?? '')
}

function listSummary(value: FilterValue, exclude: boolean): string {
	const values = (Array.isArray(value) ? value : [value]).filter((v) => v != null && v !== '')
	const shown = values.slice(0, 2).join(', ')
	const rest = values.length - 2
	const text = rest > 0 ? `${shown} +${rest}` : shown
	return exclude ? `not ${text}` : text
}

/**
 * The two halves of an overview row: the column it filters, and what it filters
 * it to. The row types them differently, so they never merge into a sentence.
 */
export function summaryParts(filter: ProtoFilter): { label: string; value: string } {
	return { label: filter.column.name, value: valueSummary(filter) }
}

function valueSummary(filter: ProtoFilter): string {
	const { operator, value } = filter

	if (operator === 'is_set') return 'is set'
	if (operator === 'is_not_set') return 'is not set'
	if (operator === 'contains') return `contains ${value}`
	if (operator === 'in' || operator === 'not_in') {
		return listSummary(value, operator === 'not_in')
	}

	if (kindOf(filter.column.type) === 'date') {
		if (operator === 'within') {
			const span = value as Timespan
			if (isDaySpan(span)) return formatDay(span.anchor!)
			return presetLabel(span?.span || '')
		}
		if (operator === 'between') {
			const [from, to] = (value as string[]) || []
			return formatRange(from, to)
		}
	}

	if (operator === 'between') {
		const [from, to] = (value as any[]) || []
		return `${formatNumber(from)} to ${formatNumber(to)}`
	}
	if (operator === '>=') return `at least ${formatNumber(value)}`
	if (operator === '<=') return `at most ${formatNumber(value)}`

	return String(value ?? '')
}
