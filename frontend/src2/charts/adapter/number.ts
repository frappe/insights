import type { NumberCardProps, NumberCardSparkline } from 'frappe-ui/charts'
import { granularityOptions } from '../../helpers/constants'
import { __ } from '../../translation'
import type { NumberChartConfig } from '../../types/chart.types'
import type { Dimension, Measure, QueryResultRow } from '../../types/query.types'
import NumberCards from './NumberCards.vue'
import type { ChartAdapterInput, ChartFiller } from './types'

// A Number Chart carries several Measures and v2's card is one reading, so the
// filler is a grid Insights lays out with one card behind each value. Two more
// things v2 will not do for a caller land here as arithmetic: the comparison
// delta, and the scaling a Measure formatted as a percent asks for.

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
	// whole grid — the comparison reads the one before it.
	const current = rows[rows.length - 1]
	if (!current) return

	const cards = measures.map((measure, index) => readingOf(config, rows, measure, index))

	return {
		component: NumberCards,
		props: { cards },
		// every reading is a card in its own right, so the chrome draws none
		// around the grid they sit in
		card: false,
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
): NumberCardEntry {
	const column = measure.measure_name
	const readings = rows.map((row) => toNumber(row[column]))
	const latest = readings[readings.length - 1] ?? null

	// A Measure formatted as a percent holds the fraction, so Insights scales it
	// and states the unit. What a number means is the caller's; v2 prints it.
	const percent = measure.format === 'percent'

	// Set per value, falling back to what the Chart set for all of them. `color`
	// is per value alone: it is the ink of one reading, and a Chart that colored
	// every reading the same has said nothing.
	const options = config.number_column_options?.[index] || {}
	const prefix = options.prefix ?? config.prefix
	const suffix = options.suffix ?? config.suffix
	const precision = options.decimal ?? config.decimal
	const compact = options.shorten_numbers ?? config.shorten_numbers

	const card: NumberCardEntry = {
		column,
		title: column,
		value: latest !== null && percent ? latest * 100 : latest,
	}
	if (options.color) card.color = options.color
	if (prefix) card.prefix = prefix
	const unit = percent ? `%${suffix || ''}` : suffix
	if (unit) card.suffix = unit
	if (precision !== undefined) card.precision = precision
	if (compact) card.compact = true

	if (config.comparison) {
		card.delta = percentChange(readings)
		card.deltaSuffix = '%'
		const caption = comparisonCaption(config.date_column)
		if (caption) card.deltaCaption = caption
		if (config.negative_is_better) card.negativeIsBetter = true
	}

	if (config.sparkline && config.date_column?.column_name) {
		const sparkline: NumberCardSparkline = { data: readings }
		if (config.sparkline_color) sparkline.color = config.sparkline_color
		card.sparkline = sparkline
	}

	return card
}

/**
 * The change from the reading before last to the last, as a share of it. Signed
 * the way the data moved: v2 flips the colors for a metric where down is
 * better, so flipping the number here too would flip it back.
 *
 * Nothing to compare against, or nothing to compare with — one reading, or a
 * previous one of zero — leaves the card with no delta. A change from nothing
 * has no percentage.
 */
function percentChange(readings: (number | null)[]): number | null {
	const current = readings[readings.length - 1]
	const previous = readings[readings.length - 2]
	if (current === null || current === undefined) return null
	if (previous === null || previous === undefined || previous === 0) return null
	return ((current - previous) / Math.abs(previous)) * 100
}

/** What the delta is measured against: the period the date column groups by. */
function comparisonCaption(dimension?: Dimension): string | undefined {
	const grain = granularityOptions.find((option) => option.value === dimension?.granularity)
	return grain && __('vs previous {0}', grain.label.toLowerCase())
}

/** A reading with no number is not a zero, so a missing one stays missing. */
function toNumber(value: any): number | null {
	if (value === null || value === undefined || value === '') return null
	const number = Number(value)
	return Number.isNaN(number) ? null : number
}
