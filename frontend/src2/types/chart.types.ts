import { Dimension, Measure } from './query.types'

export const AXIS_CHARTS = ['Bar', 'Line', 'Row']
export type AxisChartType = (typeof AXIS_CHARTS)[number]

export const CHARTS = ['Number', ...AXIS_CHARTS, 'Donut', 'Funnel', 'Table']
export type ChartType = (typeof CHARTS)[number]

export type AxisChartConfig = {
	x_axis: XAxis
	y_axis: YAxis
	split_by?: SplitBy
}

export type XAxis = {
	dimension: Dimension
	label_rotation?: number
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
	show_scrollbar?: boolean
}
export type Series = {
	name?: string
	measure: Measure
	color?: string[]
	type?: 'line' | 'bar'
	align?: 'Left' | 'Right'
	show_data_labels?: boolean
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

export type NumberChartConfig = {
	number_columns: Measure[]
	number_column_options: NumberColumnOptions[]
	comparison: boolean
	sparkline: boolean
	sparkline_color?: string
	date_column?: Dimension
	shorten_numbers?: boolean
	decimal?: number
	prefix?: string
	suffix?: string
	negative_is_better?: boolean
}
export type NumberColumnOptions = {
	shorten_numbers?: boolean
	decimal?: number
	prefix?: string
	suffix?: string
}

export type DonutChartConfig = {
	label_column: Dimension
	value_column: Measure
	legend_position?: 'top' | 'bottom' | 'left' | 'right'
	max_slices?: number
	show_inline_labels?: boolean
}
export type FunnelChartConfig = {
	label_column: Dimension
	value_column: Measure
	label_position?: 'left' | 'right' | 'alternate'
}

export type TableChartConfig = {
	rows: Dimension[]
	columns: Dimension[]
	values: Measure[]
	max_column_values?: number
	show_filter_row?: boolean
	show_row_totals?: boolean
	show_column_totals?: boolean
	enable_color_scale?: boolean
	sticky_columns?: string[]
}

export type ChartConfig =
	| LineChartConfig
	| BarChartConfig
	| NumberChartConfig
	| DonutChartConfig
	| TableChartConfig
	| FunnelChartConfig
