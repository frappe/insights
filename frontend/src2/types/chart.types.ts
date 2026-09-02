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

export type AxisChartConfig = {
	x_axis: XAxis
	y_axis: YAxis
	split_by?: SplitBy
}

export type XAxis = {
	dimension: Dimension
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
	color?: string
	dashed?: boolean
}
export type Series = {
	name?: string
	measure: Measure
	color?: string[]
	type?: 'line' | 'bar'
	align?: 'Left' | 'Right'
	show_data_labels?: boolean
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
	 * `previous` is the row before the last one, `constant` a fixed number,
	 * `measure` a measure of the card's own query read off the same last row, and
	 * `window` the chart's own window shifted back. A shifted window is derived as
	 * the row before the last one, so it reads the same way `previous` does.
	 */
	source: 'previous' | 'constant' | 'measure' | 'window'
	/** The number, when `source` is `constant`. */
	value?: number
	/** The measure holding it, when `source` is `measure`. */
	measure?: Measure
	/** The same span, anchored `count` `unit`s away. `source: 'window'` only. */
	shift?: { unit: string; count: number }
	/**
	 * How the gap is printed: `change` as a percent of the comparison number,
	 * `delta` as a signed number in the value's own units. Defaults to `change`.
	 */
	show?: NumberComparisonShow
	/** What to call it, e.g. `vs last month`. Defaults from the source. */
	label?: string
}
export type NumberComparisonShow = 'change' | 'delta'

export type NumberChartConfig = {
	number_columns: Measure[]
	number_column_options: NumberColumnOptions[]
	sparkline: boolean
	sparkline_color?: string
	date_column?: Dimension
	/**
	 * The period the card reads. Needs `date_column`: the window is a group-by on
	 * it, one row per window, so the card reads the newest window and compares it
	 * with the one a `window` comparison shifts to.
	 */
	window?: {
		/** A span the engine understands, e.g. `month to date`. */
		span: string
		/** Fixed anchor for a card that must not move with today. Defaults to today. */
		anchor?: string
	}
	/**
	 * What every value falls back to. The form no longer writes these — it sets
	 * them per value — but a chart saved before it did still reads them.
	 */
	shorten_numbers?: boolean
	decimal?: number
	prefix?: string
	suffix?: string
	negative_is_better?: boolean
	/** Set by a release before the per-value shape. Reads as one `previous` comparison. */
	comparison?: boolean
}
export type NumberColumnOptions = {
	shorten_numbers?: boolean
	decimal?: number
	prefix?: string
	suffix?: string
	color?: string
	/** A fall is the good news, e.g. churn or cost. Flips the comparison's colors. */
	negative_is_better?: boolean
	/** What the reading is aimed at. A target belongs to the metric, not to the chart. */
	target?: NumberTarget
	/**
	 * The one number the reading is compared with. Absent falls back to the
	 * chart's `comparison` flag; a value that names none compares nothing.
	 */
	comparison?: NumberComparison
}

export type DonutChartConfig = {
	label_column: Dimension
	value_column: Measure
	legend_position?: 'top' | 'bottom' | 'left' | 'right'
	max_slices?: number
	show_inline_labels?: boolean
}
export type FunnelChartConfig = {
	// Measures mode: each measure is one funnel stage, aggregated over the whole
	// result with no group-by (stage label = measure name). Takes precedence when set.
	measures?: Measure[]
	// Grouped (long-format) mode: group `label_column` and read `value_column` per row.
	label_column?: Dimension
	value_column?: Measure
	show_percentage?: boolean
}

export type TableChartConfig = {
	rows: Dimension[]
	columns: Dimension[]
	values: Measure[]
	max_column_values?: number
	show_filter_row?: boolean
	show_row_totals?: boolean
	show_column_totals?: boolean
	compact_numbers?: boolean
	enable_color_scale?: boolean
	sticky_columns?: string[]
	column_widths?: Record<string, number>
	text_wrap?: Record<string, boolean>
	conditional_formatting?: FormatGroupArgs
}

export type MapChartConfig = {
	location_column: Dimension
	value_column: Measure
	map_type?: 'world' | 'india'
	region_mappings?: {
		world?: Record<string, string>
		india?: Record<string, string>
	}
}

export type BubbleChartConfig = {
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

export type SankeyChartConfig = {
	source_column: Dimension
	target_column: Dimension
	value_column: Measure
	orient?: 'horizontal' | 'vertical'
	node_align?: 'left' | 'right' | 'justify'
}

export type HeatmapChartConfig = {
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
