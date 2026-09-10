import { GranularityType } from '../helpers/constants'
import { FormatGroupArgs } from '../query/components/formatting_utils'
import { Dimension, Measure } from './query.types'

export const AXIS_CHARTS = ['Bar', 'Line', 'Row']
export type AxisChartType = (typeof AXIS_CHARTS)[number]

export const CHARTS = [
	'Number',
	...AXIS_CHARTS,
	'Donut',
	'Funnel',
	'Table',
	'Map',
	'Bubble',
	'Sankey',
	'Heatmap',
]
export type ChartType = (typeof CHARTS)[number]

/**
 * How a number prints. One shape, written by every layer that has a say — the
 * chart's own default, and each Measure's override of it — so a setting reads
 * the same wherever it was set.
 *
 * What it does not carry is the unit: a currency or a percent is the Measure's
 * own `format`, stated once on the Measure and printed by every chart that
 * draws it. This is the display on top of that.
 */
export type NumberFormat = {
	/** `12300` prints as `12.3K`. */
	shorten?: boolean
	/** Decimal places. Left out, a value keeps as many as it carries, up to two. */
	decimals?: number
	/** Printed before the number. Set, it stands in for the Measure's own unit. */
	prefix?: string
	/** Printed after the number. Set, it stands in for the Measure's own unit. */
	suffix?: string
}

/**
 * Every chart config carries these two. `number_format` is the chart's default,
 * which each of its values inherits. `number_formats` is one Measure's own,
 * keyed by `measure_name`, and it overrides the default key by key.
 *
 * A chart drawing one measure has nothing to tell apart, so its form writes the
 * Measure's entry alone and leaves the default empty.
 */
export type NumberFormatConfig = {
	number_format?: NumberFormat
	number_formats?: Record<string, NumberFormat>
}

export type AxisChartConfig = NumberFormatConfig & {
	x_axis: XAxis
	y_axis: YAxis
	split_by?: SplitBy
	tooltip?: Tooltip
}

export type XAxis = {
	dimension: Dimension
}

/**
 * Measures that reach the tooltip and nothing else: no series, no legend entry,
 * no place on the value axis. For context in another unit — the count behind a
 * rate, the target beside the actual.
 *
 * Its own key rather than a flag on a Series, because it is not a Series: a
 * Series that draws nothing is the thing `hide_from_chart` already is.
 *
 * A Dimension cannot go here. The chart's rows are a summarize, so anything in
 * the tooltip must be one value per plotted row, and only an aggregate is. A
 * constant attribute is reached by picking its text column with `min`.
 */
export type Tooltip = {
	measures: Measure[]
}

export type SplitBy = {
	dimension: Dimension
	max_split_values?: number
}

export type YAxis = {
	series: Series[]
	min?: number
	max?: number
	axis_label?: string
	show_axis_label?: boolean
	show_data_labels?: boolean
	reference_lines?: ReferenceLine[]
}
export type ReferenceAggregate = 'average' | 'median' | 'min' | 'max' | 'sum'
export type ReferenceLine = {
	// 'y' draws a horizontal line at a measure value, 'x' a vertical line at a category/date value
	axis?: 'x' | 'y'
	// which value axis a 'y' line targets on a dual-axis chart; defaults to the primary (left)
	align?: 'Left' | 'Right'
	// A line sits at a constant, or at an aggregate of one of the chart's own
	// Measures. The Measure is named rather than copied: the series holds the
	// definition, so a copy is a second answer waiting to disagree.
	value?: number | string
	measure_name?: string
	aggregate?: ReferenceAggregate
	// What develop called the same thing before this branch named it `aggregate`.
	// Charts saved on develop carry it, so normalizeChartConfig reads it and drops it.
	statistic?: ReferenceAggregate | null
	label?: string
	// Which end of the rule the label sits at, and which side of it. Left unset,
	// the rule labels itself at its far end, above it.
	label_placement?: ReferenceLabelPlacement
	color?: string
	dashed?: boolean
}
export type ReferenceLabelPlacement = 'start-top' | 'start-bottom' | 'end-top' | 'end-bottom'
export type Series = {
	name?: string
	measure: Measure
	color?: string[]
	type?: 'line' | 'bar'
	align?: 'Left' | 'Right'
	show_data_labels?: boolean
	// A series drawn at zero opacity and kept out of the legend, i.e. a Measure
	// that reached the tooltip and nothing else. `tooltip.measures` says that,
	// so normalizeChartConfig moves it there. Read, never written.
	hide_from_chart?: boolean
}
export type YAxisLine = Series & {
	series: SeriesLine[]
	smooth?: boolean
	show_data_points?: boolean
	show_area?: boolean

}
export type SeriesLine = Series & {
	type: 'line'
	smooth?: boolean
	show_data_points?: boolean
	show_area?: boolean
}
export type YAxisBar = Series & {
	series: SeriesBar[]
	stack?: boolean
	normalize?: boolean
	overlap?: boolean
}
export type SeriesBar = Series & {
	type: 'bar'
}

export type BarChartConfig = AxisChartConfig & {
	y_axis: YAxisBar
}
export type LineChartConfig = AxisChartConfig & {
	y_axis: YAxisLine
}
export type MixedChartConfig = AxisChartConfig & {
	y_axis: YAxisLine | YAxisBar
}

/**
 * What the reading is aimed at. The card prints it on the value line, as
 * `$621.8K / $750K`: a target is part of the reading, not commentary on it, so
 * it carries no label and no percent — the fraction is the whole statement.
 */
export type NumberTarget = {
	/** A fixed number. */
	value?: number
	/** A measure of the card's own query, read off the row the reading came from. */
	measure?: Measure
}

/**
 * The one number the reading is compared with, printed in the delta row with an
 * arrow and a color. One, not a list: a second comparison is a second card, and
 * that is the dashboard's job.
 */
export type NumberComparison = {
	/**
	 * The question, not the way it is answered: `previous` is the period before
	 * the one on the card and `last year` is the same period a year earlier,
	 * both of which the card's own period is what fetches — a span shifts its
	 * window back, a grain already holds the row. `constant` is a fixed number,
	 * and `measure` a measure of the card's own query read off the same last row.
	 *
	 * A period a question cannot be put to answers nothing: only a span can be
	 * anchored a year back, so `last year` beside a grain prints no delta.
	 */
	source: 'previous' | 'last year' | 'constant' | 'measure'
	/** The number, when `source` is `constant`. */
	value?: number
	/** The measure holding it, when `source` is `measure`. */
	measure?: Measure
	/**
	 * How the gap is printed: `change` as a percent of the comparison number,
	 * `delta` as a signed number in the value's own units. Defaults to `change`.
	 */
	show?: NumberComparisonShow
	/** What to call it, e.g. `vs last month`. Defaults from the source. */
	label?: string
}
export type NumberComparisonShow = 'change' | 'delta'

export type NumberChartConfig = NumberFormatConfig & {
	number_columns: Measure[]
	number_column_options: NumberColumnOptions[]
	sparkline: boolean
	sparkline_color?: string
	date_column?: Dimension
	/**
	 * The period the card reads, and the only thing that groups it by date.
	 * Needs `date_column`. A period names one of two group-bys, never both:
	 *
	 * - `span` filters to a stretch of the calendar and groups by which stretch
	 *   a row fell in. One row per stretch, so the card reads the newest and a
	 *   period comparison shifts the window to an earlier one.
	 * - `grain` filters nothing and groups by the date grain. One row per
	 *   period present in the data, so the card reads the newest one there and
	 *   a `previous` comparison reads the row before it.
	 *
	 * Left out, the card is one number over the whole result and the date column
	 * only feeds the sparkline. Before this existed a granularity on
	 * `date_column` did what `grain` does, which is what `periodOf` reads.
	 */
	window?: {
		/** A span the engine understands, e.g. `month to date`. */
		span?: string
		/** A date grain, e.g. `month`. Mutually exclusive with `span`. */
		grain?: GranularityType
		/** Fixed anchor for a card that must not move with today. Defaults to today. */
		anchor?: string
	}
	/**
	 * How every value printed, before `number_format` said it for every chart
	 * type. The forms no longer write these. The resolver reads them as the
	 * chart's default, so a chart nobody opens keeps printing as it did.
	 */
	shorten_numbers?: boolean
	decimal?: number
	prefix?: string
	suffix?: string
	negative_is_better?: boolean
}
export type NumberColumnOptions = {
	/**
	 * How this value printed, before `number_formats` said it for every chart
	 * type. Read as this Measure's own format, under anything `number_formats`
	 * sets for it.
	 */
	shorten_numbers?: boolean
	decimal?: number
	prefix?: string
	suffix?: string
	color?: string
	/** A fall is the good news, e.g. churn or cost. Flips the comparison's colors. */
	negative_is_better?: boolean
	/** What the reading is aimed at. A target belongs to the metric, not to the chart. */
	target?: NumberTarget
	/** The one number the reading is compared with. Naming none compares nothing. */
	comparison?: NumberComparison
}

export type DonutChartConfig = NumberFormatConfig & {
	label_column: Dimension
	value_column: Measure
	max_slices?: number
	show_inline_labels?: boolean
}
export type FunnelChartConfig = NumberFormatConfig & {
	// Measures mode: each measure is one funnel stage, aggregated over the whole
	// result with no group-by (stage label = measure name). Takes precedence when set.
	measures?: Measure[]
	// Grouped (long-format) mode: group `label_column` and read `value_column` per row.
	label_column?: Dimension
	value_column?: Measure
	show_percentage?: boolean
}

export type TableChartConfig = NumberFormatConfig & {
	rows: Dimension[]
	columns: Dimension[]
	values: Measure[]
	max_column_values?: number
	show_filter_row?: boolean
	show_row_totals?: boolean
	show_column_totals?: boolean
	/** What `number_format.shorten` says now. Read as the chart's default. */
	compact_numbers?: boolean
	enable_color_scale?: boolean
	sticky_columns?: string[]
	column_widths?: Record<string, number>
	text_wrap?: Record<string, boolean>
	conditional_formatting?: FormatGroupArgs
}

export type MapChartConfig = NumberFormatConfig & {
	location_column: Dimension
	value_column: Measure
	map_type?: 'world' | 'india'
	region_mappings?: {
		world?: Record<string, string>
		india?: Record<string, string>
	}
}

export type BubbleChartConfig = NumberFormatConfig & {
	xAxis: Measure
	yAxis: Measure
	size_column?: Measure
	dimension?: Dimension
	quadrant_column?: Dimension
	show_data_labels?: boolean
	show_quadrants?: boolean
	xAxis_refLine?: number
	yAxis_refLine?: number
}

export type SankeyChartConfig = NumberFormatConfig & {
	source_column: Dimension
	target_column: Dimension
	value_column: Measure
	orient?: 'horizontal' | 'vertical'
	node_align?: 'left' | 'right' | 'justify'
}

export type HeatmapChartConfig = NumberFormatConfig & {
	// The two dimensions the grid is cut by: `x_column` runs along the bottom,
	// `y_column` up the side. One cell is one pair of their values.
	x_column: Dimension
	y_column: Dimension
	value_column: Measure
	show_values?: boolean
	// 'sequential' reads as a magnitude, 'diverging' centers on zero for signed data
	palette?: 'sequential' | 'diverging'
	min?: number
	max?: number
}

export type ChartConfig =
	| LineChartConfig
	| BarChartConfig
	| NumberChartConfig
	| DonutChartConfig
	| TableChartConfig
	| FunnelChartConfig
	| MapChartConfig
	| BubbleChartConfig
	| SankeyChartConfig
	| HeatmapChartConfig

export interface Suggestion {
		region: string
		similarity: number
	}

export interface Region {
		user_region: string
		mapped_to?: string
		suggestions?: Suggestion[]
	}

export interface MappingData {
		total: number
		resolved: number
		unresolved: number
		unresolved_list: Region[]
		manual_mappings: Record<string, string>
		available_regions: string[]
	}
