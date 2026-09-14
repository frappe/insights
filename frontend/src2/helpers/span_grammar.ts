// The relative-span grammar, written once for this runtime.
//
// A span is a string, and every surface that offers one writes it in this
// grammar:
//
//   `<unit> to date`            the period so far, up to the anchor
//   `current <unit>`            the whole period the anchor falls in
//   `last <N> <unit>s`          N whole periods behind the current one
//   `next <N> <unit>s`          N whole periods ahead of it
//   `… (include current)`       extends a `last` or `next` span over the
//                               period the anchor falls in
//
// A `last` or `next` span that names no count covers one period: "last month"
// reads as "last 1 month". `<unit>` is one of `SPAN_UNITS`, singular or plural.
//
// The server reads the same grammar, in `parse_span`
// (`insights/insights/query_builders/sql_functions.py`), and `get_window` there
// is what a span finally resolves against. Two parsers, one grammar: a span this
// module writes is a span the server runs, and a change to either side is a
// change to this comment first.

export const SPAN_UNITS = ['day', 'week', 'month', 'quarter', 'year', 'fiscal year'] as const
export type SpanUnit = (typeof SPAN_UNITS)[number]

export type SpanShape = 'to date' | 'current' | 'last' | 'next'

export type Span = {
	shape: SpanShape
	unit: SpanUnit
	/** How many whole periods a `last` or `next` span covers. One otherwise. */
	count: number
	/** Extends a `last` or `next` span over the current period. */
	includeCurrent: boolean
}

const INCLUDE_CURRENT = '(include current)'

/** The unit a typed word names. Typing stays in English, as the spans are. */
export function spanUnitOf(word?: string): SpanUnit | undefined {
	const unit = word?.trim().toLowerCase().replace(/s$/, '')
	return SPAN_UNITS.find((candidate) => candidate === unit)
}

/** The span a form is written as. */
export function buildSpan(span: Span): string {
	if (span.shape === 'to date') return `${span.unit} to date`
	if (span.shape === 'current') return `current ${span.unit}`

	const count = Math.max(1, Math.round(span.count || 1))
	const unit = count === 1 ? span.unit : `${span.unit}s`
	return `${span.shape} ${count} ${unit}${span.includeCurrent ? ` ${INCLUDE_CURRENT}` : ''}`
}

/** The form behind a span, or nothing where the string is not one. */
export function parseSpan(span?: string): Span | undefined {
	if (!span) return undefined

	let rest = span.trim().toLowerCase().replace(/\s+/g, ' ')
	const includeCurrent = rest.includes(INCLUDE_CURRENT)
	rest = rest.replace(INCLUDE_CURRENT, '').trim()

	if (rest.endsWith('to date')) {
		const unit = spanUnitOf(rest.slice(0, -'to date'.length))
		// A count and "to date" cannot both be said: the period so far is one
		// period, so "last 7 days to date" names nothing.
		return unit ? { shape: 'to date', unit, count: 1, includeCurrent: false } : undefined
	}

	const [first, ...words] = rest.split(' ')

	if (first === 'current') {
		const unit = spanUnitOf(words.join(' '))
		return unit ? { shape: 'current', unit, count: 1, includeCurrent: false } : undefined
	}

	if (first !== 'last' && first !== 'next') return undefined

	const counted = Number(words[0])
	const count = Number.isFinite(counted) && counted > 0 ? counted : 1
	const unit = spanUnitOf((Number.isFinite(counted) ? words.slice(1) : words).join(' '))
	return unit ? { shape: first, unit, count, includeCurrent } : undefined
}
