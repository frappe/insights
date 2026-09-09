import type { NumberCardProps, NumberCardSparkline } from 'frappe-ui/charts'
import { ROW_HEIGHT } from '../../dashboard/grid_placement'
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
import { numberFormatOf } from '../number_format'
import { windowShiftLabel } from '../window'
import NumberCards from './NumberCards.vue'
import type { ChartAdapterInput, ChartFiller } from './types'

// A Number Chart carries several Measures and v2's card is one reading, so a
// reading is a card and the chart is the row of them. Two more things v2 will
// not do for a caller land here as arithmetic: the gap against the comparison,
// and the scaling a Measure formatted as a percent asks for.
//
// The one type that takes no `format` prop: v2's card prints a target and a
// delta beside the reading and formats all three from props of its own. So the
// resolver is asked for the format rather than for a formatter, and the pieces
// are mapped across.

/** One reading: a card, and the result column it was read off. */
export type NumberCardEntry = NumberCardProps & {
	/** Name of the result column behind the reading. What a drill names. */
	column: string
	/** The chart states no such reading any more. See `cardFor`. */
	missing?: boolean
	/** The card's height in px, as a cell of `numberCardRows` rows gives it. */
	height: number
}

export type NumberCardClickEvent = { column: string }

export function adaptNumberChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as NumberChartConfig
	if (!numberReadings(config).length) return

	// The config names every reading, so the cards are built before a result and
	// built when none arrives: a card with no row prints a dash, and the states
	// the other types wear on their chrome are drawn inside them.
	const rows = input.result.rows || []
	// Every reading is the newest one, so the newest row is the row behind every
	// card — a `previous` comparison reads the one before it.
	const current = rows[rows.length - 1]

	// A dashboard cell names the one reading it draws. A surface that names none
	// — the workbook editor — previews them all.
	const drawn = input.column ? [input.column] : numberReadings(config)
	const cards = drawn.map((column) => cardFor(config, rows, column, input.sparklineResult?.rows))

	// A surface that names no reading gets the cards at the size a cell gives
	// them, so the preview is what the dashboard draws and not a guess at it.
	const filler: ChartFiller = {
		component: NumberCards,
		props: { cards, preview: !input.column },
	}
	// Nothing to drill into until there is a row behind the reading.
	if (current) {
		filler.drillDown = {
			cardClick: (event: NumberCardClickEvent) => ({
				column: event.column,
				row: current,
			}),
		}
	}
	return filler
}

/** The readings a Number Chart states, in the order it states them. */
export function numberReadings(config: NumberChartConfig): string[] {
	return (config.number_columns || [])
		.filter((measure) => measure?.measure_name)
		.map((measure) => measure.measure_name)
}

/**
 * Where a reading sits in the config, which is also where its settings sit —
 * `number_column_options` stands beside `number_columns` by position, unnamed
 * entries included. `-1` when the config states no such reading.
 *
 * Naming none is naming the first: a cell written before a cell could name one
 * draws what it has always drawn.
 */
function readingIndex(config: NumberChartConfig, column?: string): number {
	const columns = config.number_columns || []
	return column
		? columns.findIndex((measure) => measure?.measure_name === column)
		: columns.findIndex((measure) => measure?.measure_name)
}

/**
 * The card behind one reading.
 *
 * A cell can name a reading the chart no longer states — an author renamed the
 * Measure, or removed it. The card stands where it stood and says so, rather
 * than the cell vanishing under an author who never asked for that.
 */
function cardFor(
	config: NumberChartConfig,
	rows: QueryResultRow[],
	column: string,
	series?: QueryResultRow[],
): NumberCardEntry {
	const index = readingIndex(config, column)
	const measure = (config.number_columns || [])[index]
	const height = numberCardHeight(config, column)
	if (!measure) return { column, title: column, value: null, missing: true, height }
	return { ...readingOf(config, rows, measure, index, series), height }
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
	// and the format states the unit. What a number means is the caller's.
	const format = numberFormatOf(config, measure)
	const scale = (reading: number | null) => (reading !== null ? reading * format.scale : reading)

	// `color` is per value alone: it is the ink of one reading, and a Chart that
	// colored every reading the same has said nothing.
	const options = config.number_column_options?.[index] || {}
	const negativeIsBetter = options.negative_is_better ?? config.negative_is_better

	const card: NumberCardEntry = {
		column,
		title: column,
		value: scale(latest),
	}
	if (options.color) card.color = options.color
	if (format.prefix) card.prefix = format.prefix
	if (format.suffix) card.suffix = format.suffix
	if (format.decimals !== undefined) card.precision = format.decimals
	if (format.shorten) card.compact = true

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
				if (format.prefix) card.deltaPrefix = format.prefix
				// A percent Measure's gap is points, not percent: the reading and its
				// comparison are both percentages, so the shift between them is a
				// change in percentage points, not a further percent change. Every
				// other unit already stands on the value line above, and repeating
				// it here only crowds the delta row out of its single line.
				if (measure.format === 'percent') card.deltaSuffix = ' ' + __('pts')
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

// ------------------------------------------------------------ the cell height

/**
 * The card, measured from the CSS that draws it — every number below is a class
 * on `NumberCard.vue` or on frappe-ui's `ChartCard`, resolved against the type
 * scale, and nothing here is an estimate.
 */
const CARD = {
	/** A dashboard cell's `p-2`, top and bottom. */
	cellPadding: 2 * 8,
	/** ChartCard's `py-3` and its 1px border, top and bottom. */
	chrome: 2 * (12 + 1),
	/** `gap-1.5` between the card's blocks. */
	gap: 6,
	/** The title: `text-sm`, 13px at a line height of 1.15. */
	title: 13 * 1.15,
	/** The reading: `text-3xl-semibold`, 20px at 1.15. */
	value: 20 * 1.15,
	/** The delta row: a `size-4` arrow, which stands taller than its own text. */
	delta: 16,
	/** `pb-10`, the band the sparkline is drawn into. */
	sparkline: 40,
}

/**
 * The rows one reading of a Number Chart takes as a dashboard cell.
 *
 * A card's height is what its blocks add up to, so the author sets the width and
 * the height follows the config. There are three of them: a title and a reading,
 * a delta row under them when the reading is compared with something, and the
 * sparkline band under that.
 *
 * A cell that names nothing draws the first reading. One naming a reading the
 * chart dropped keeps the height the chart's own settings give it, so the cell
 * does not move under the author while they decide what to do about it.
 */
export function numberCardRows(config: NumberChartConfig, column?: string): number {
	const options = config.number_column_options?.[readingIndex(config, column)] || {}
	const { comparison } = measuredAgainst(config, options)
	const sparkline = Boolean(config.sparkline && config.date_column?.column_name)

	let height = CARD.cellPadding + CARD.chrome + CARD.title + CARD.gap + CARD.value
	if (comparison || sparkline) height += CARD.gap + CARD.delta
	if (sparkline) height += CARD.sparkline

	return Math.ceil(height / ROW_HEIGHT)
}

/** The card's own height in a cell of `numberCardRows` rows: the rows less the cell's padding. */
export function numberCardHeight(config: NumberChartConfig, column?: string): number {
	return numberCardRows(config, column) * ROW_HEIGHT - CARD.cellPadding
}

/** The shortest a Number cell gets: a title and a reading, nothing under them. */
export const NUMBER_CARD_MIN_ROWS = numberCardRows({} as NumberChartConfig)
