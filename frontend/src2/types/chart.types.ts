import { Dimension, Measure } from "./query.types"

export const AXIS_CHARTS = ['Bar', 'Line']
export type AxisChartType = (typeof AXIS_CHARTS)[number]

export const CHARTS = ['Number', ...AXIS_CHARTS, 'Donut', 'Table']
export type ChartType = (typeof CHARTS)[number]

export type AxisChartConfig = {
	x_axis: Dimension
	y_axis: Measure[]
	y2_axis?: Measure[]
	y2_axis_type?: 'line' | 'bar'
	split_by: Dimension
	show_data_labels?: boolean
}
export type BarChartConfig = AxisChartConfig & {
	stack?: boolean
	normalize?: boolean
	swap_axes?: boolean
}
export type LineChartConfig = AxisChartConfig & {
	smooth?: boolean
	show_data_points?: boolean
	show_area?: boolean
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
}

export type TableChartConfig = {
	rows: Dimension[]
	columns: Dimension[]
	values: Measure[]
}

export type ChartConfig = AxisChartConfig | NumberChartConfig | DountChartConfig | TableChartConfig
