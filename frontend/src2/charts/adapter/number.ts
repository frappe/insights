import type { NumberCardProps, NumberCardSparkline } from 'frappe-ui/charts'
import { toNumber } from '../../helpers'
import { granularityOptions } from '../../helpers/constants'
import { __ } from '../../translation'
import type {
	NumberChartConfig,
	NumberColumnOptions,
	NumberComparison,
	NumberTarget,
} from '../../types/chart.types'
import type { Dimension, Measure, QueryResultRow } from '../../types/query.types'
import { windowShiftLabel } from '../window'
import NumberCards from './NumberCards.vue'
import type { ChartAdapterInput, ChartFiller } from './types'

// A Number Chart carries several Measures and v2's card is one reading, so the
// filler is a grid Insights lays out with one card behind each value. Two more
// things v2 will not do for a caller land here as arithmetic: the gap against
// the comparison, and the scaling a Measure formatted as a percent asks for.

/** One reading of the grid: a card, and the result column it was read off. */
export type NumberCardEntry = NumberCardProps & {
	/** Name of the result column behind the reading. Its identity in the grid. */
	column: string
}

export type NumberCardClickEvent = { column: string }

export function adaptNumberChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as NumberChartConfig
	const measures = (config.number_columns || []).filter((measure) => measure.measure_name)
	if (!measures.length) return

	const rows = input.result.rows
	// Every reading is the newest one, so the newest row is the row behind the
	// whole grid — a `previous` comparison reads the one before it.
	const current = rows[rows.length - 1]
	if (!current) return

	const series = input.sparklineResult?.rows
	const cards = measures.map((measure, index) => readingOf(config, rows, measure, index, series))

	return {
		component: NumberCards,
		props: { cards },
		drillDown: {
			cardClick: (event: NumberCardClickEvent) => ({
				column: event.column,
				row: current,
			}),
		},
	}
}

function readingOf(
	config: NumberChartConfig,
	rows: QueryResultRow[],
	measure: Measure,
	index: number,
	series?: QueryResultRow[],
): NumberCardEntry {
	const column = measure.measure_name
	const readings = rows.map((row) => toNumber(row[column]))
	const latest = readings[readings.length - 1] ?? null

	// A Measure formatted as a percent holds the fraction, so Insights scales it
	// and states the unit. What a number means is the caller's; v2 prints it.
	const percent = measure.format === 'percent'
	const scale = (reading: number | null) =>
		reading !== null && percent ? reading * 100 : reading

	// Set per value, falling back to what the Chart set for all of them. `color`
	// is per value alone: it is the ink of one reading, and a Chart that colored
	// every reading the same has said nothing.
	const options = config.number_column_options?.[index] || {}
	const prefix = options.prefix ?? config.prefix
	const suffix = options.suffix ?? config.suffix
	const precision = options.decimal ?? config.decimal
	const compact = options.shorten_numbers ?? config.shorten_numbers
	const negativeIsBetter = options.negative_is_better ?? config.negative_is_better

	const card: NumberCardEntry = {
		column,
		title: column,
		value: scale(latest),
	}
	if (options.color) card.color = options.color
	if (prefix) card.prefix = prefix
	const unit = percent ? `%${suffix || ''}` : suffix
	if (unit) card.suffix = unit
	if (precision !== undefined) card.precision = precision
	if (compact) card.compact = true

	const { target, comparison } = measuredAgainst(config, options)

	// The raw number: it prints on the value line, in the value's own units, so
	// v2 formats it with the props the value is already formatted by.
	const aim = scale(targetNumber(target, rows) ?? null)
	if (aim !== null) card.target = aim

	if (comparison) {
		const against = comparisonNumber(comparison, rows, readings)
		if (against !== undefined) {
			const show = comparison.show ?? 'change'
			if (show === 'delta') {
				// A gap in the value's own units carries the value's own units, so
				// the percent Measure's scaling applies to it too.
				card.delta = latest === null || against === null ? null : scale(latest - against)
				if (prefix) card.deltaPrefix = prefix
				// A percent Measure's gap is points, not percent: the reading and its
				// comparison are both percentages, so the shift between them is a
				// change in percentage points, not a further percent change. Every
				// other unit already stands on the value line above, and repeating
				// it here only crowds the delta row out of its single line.
				if (percent) card.deltaSuffix = ' ' + __('pts')
			} else {
				card.delta = percentChange(latest, against)
				card.deltaSuffix = '%'
			}
			const label = comparison.label || defaultLabel(comparison, config.date_column)
			if (label) card.deltaCaption = label
			if (negativeIsBetter) card.negativeIsBetter = true
		}
	}

	if (config.sparkline && config.date_column?.column_name) {
		// A windowed card is one row per window, so its own readings are the trend
		// of two windows and not of the period. The server splits the window for it
		// and sends the series beside the rows; every other card is its own series.
		const data = series ? series.map((row) => toNumber(row[column])) : readings
		const sparkline: NumberCardSparkline = { data }
		if (config.sparkline_color) sparkline.color = config.sparkline_color
		card.sparkline = sparkline
	}

	return card
}

/** The shape one release wrote: a list of references, each with its own way of printing. */
type LegacyReference = {
	source: 'previous' | 'constant' | 'measure'
	value?: number
	measure?: Measure
	show?: 'change' | 'attainment' | 'delta'
	label?: string
}

/**
 * What the value is measured against, read from whichever shape wrote it.
 *
 * Three releases have written this: the current one names a `target` and a
 * `comparison` per value; the one before it wrote a `references` list, of which
 * a movement is the comparison and an attainment the target; and the one before
 * that wrote a single chart-level `comparison` flag, which said the same thing
 * as one `previous` comparison. A value that names its own answers for itself,
 * including when it names none — an author who removed the last one meant to.
 */
export function measuredAgainst(
	config: NumberChartConfig,
	options: NumberColumnOptions,
): { target?: NumberTarget; comparison?: NumberComparison } {
	if (options.target || options.comparison) {
		return { target: options.target, comparison: options.comparison }
	}

	const references = (options as { references?: LegacyReference[] }).references
	if (references) return fromReferences(references)

	return config.comparison ? { comparison: { source: 'previous' } } : {}
}

function fromReferences(references: LegacyReference[]): {
	target?: NumberTarget
	comparison?: NumberComparison
} {
	const moves = (reference: LegacyReference) =>
		reference.show === 'change' || reference.show === 'delta' || reference.source === 'previous'

	const leading = references.findIndex(moves)
	const aim = references.findIndex(
		(reference, index) => index !== leading && reference.show === 'attainment',
	)

	const context: { target?: NumberTarget; comparison?: NumberComparison } = {}
	if (leading !== -1) {
		const reference = references[leading]
		context.comparison = {
			source: reference.source,
			...(reference.value !== undefined ? { value: reference.value } : {}),
			...(reference.measure ? { measure: reference.measure } : {}),
			show: reference.show === 'delta' ? 'delta' : 'change',
			...(reference.label ? { label: reference.label } : {}),
		}
	}
	if (aim !== -1) {
		const reference = references[aim]
		context.target = reference.measure
			? { measure: reference.measure }
			: { value: reference.value }
	}
	return context
}

/** The number the reading is aimed at, or `undefined` when nothing names one. */
function targetNumber(
	target: NumberTarget | undefined,
	rows: QueryResultRow[],
): number | null | undefined {
	if (!target) return undefined
	if (typeof target.value === 'number') return target.value
	const column = target.measure?.measure_name
	if (!column) return undefined
	// Read off the same row the reading came from: a target is the target for the
	// period on the card, not for the whole series.
	return toNumber(rows[rows.length - 1]?.[column])
}

/**
 * The number the reading is held against, or `undefined` when the comparison
 * names nothing to hold it against and there is no delta row to print.
 */
function comparisonNumber(
	comparison: NumberComparison,
	rows: QueryResultRow[],
	readings: (number | null)[],
): number | null | undefined {
	if (comparison.source === 'constant') {
		return typeof comparison.value === 'number' ? comparison.value : undefined
	}
	if (comparison.source === 'measure') {
		const column = comparison.measure?.measure_name
		if (!column) return undefined
		return toNumber(rows[rows.length - 1]?.[column])
	}
	// The reading before last. A card with one reading still says what it would
	// have compared against, it just has no figure to print in front of it.
	return readings[readings.length - 2] ?? null
}

/**
 * The change from the comparison to the reading, as a share of it. Signed the way
 * the data moved: v2 flips the colors for a metric where down is better, so
 * flipping the number here too would flip it back.
 *
 * Nothing to compare with — a missing number, or one of zero — leaves the figure
 * empty. A change from nothing has no percentage.
 */
function percentChange(current: number | null, against: number | null): number | null {
	if (current === null || against === null || against === 0) return null
	return ((current - against) / Math.abs(against)) * 100
}

/** What the figure is measured against, when the author did not word it. */
function defaultLabel(comparison: NumberComparison, dimension?: Dimension): string | undefined {
	if (comparison.source === 'previous') return previousLabel(dimension)
	if (comparison.source === 'window') return windowShiftLabel(comparison.shift)
	return __('vs target')
}

/** The period the date column groups by, which is what `previous` steps back one of. */
function previousLabel(dimension?: Dimension): string | undefined {
	const grain = granularityOptions.find((option) => option.value === dimension?.granularity)
	return grain && __('vs previous {0}', grain.label.toLowerCase())
}
