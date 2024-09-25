import { Dimension, Measure } from "./query.types"

export const AXIS_CHARTS = ['Bar', 'Line']
export type AxisChartType = (typeof AXIS_CHARTS)[number]

export const CHARTS = ['Number', ...AXIS_CHARTS, 'Donut', 'Funnel', 'Table']
export type ChartType = (typeof CHARTS)[number]

export type AxisChartConfig = {
	x_axis: Dimension
	y_axis: YAxis
	split_by?: Dimension
}

export type YAxis = {
	series: Series[]
	min?: number
	max?: number
	axis_label?: string
	show_axis_label?: boolean
	show_data_labels?: boolean
}
export type Series = {
	name?: string
	measure: Measure
	color?: string[]
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
	comparison: boolean
	sparkline: boolean
	date_column?: Dimension
	shorten_numbers?: boolean
	decimal?: number
	prefix?: string
	suffix?: string
	negative_is_better?: boolean
}

export type DountChartConfig = {
	label_column: Dimension
	value_column: Measure
	legend_position?: 'top' | 'bottom' | 'left' | 'right'
}
export type FunnelChartConfig = {
	label_column: Dimension
	value_column: Measure
}

export type TableChartConfig = {
	rows: Dimension[]
	columns: Dimension[]
	values: Measure[]
	show_filter_row?: boolean
	show_row_totals?: boolean
	show_column_totals?: boolean
	conditional_formatting?: boolean
}

export type ChartConfig = LineChartConfig | BarChartConfig | NumberChartConfig | DountChartConfig | TableChartConfig | FunnelChartConfig
