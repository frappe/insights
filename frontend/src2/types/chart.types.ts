export const AXIS_CHARTS = ['Bar', 'Line']
export type AxisChartType = (typeof AXIS_CHARTS)[number]

export const CHARTS = ['Number', ...AXIS_CHARTS, 'Donut', 'Table']
export type ChartType = (typeof CHARTS)[number]

export type AxisChartConfig = {
	x_axis: string
	y_axis: string[]
	y2_axis: string[]
	y2_axis_type?: 'line' | 'bar'
	split_by?: string
	show_data_labels?: boolean
}
export type BarChartConfig = AxisChartConfig & {
	grouping?: 'stacked' | 'grouped'
	normalize?: boolean
	swap_axes?: boolean
}
export type LineChartConfig = AxisChartConfig & {}

export type NumberChartConfig = {
	number_columns: string[]
	comparison: boolean
	sparkline: boolean
	date_column?: string
	shorten_numbers?: boolean
	decimal?: number
	prefix?: string
	suffix?: string
	negative_is_better?: boolean
}

export type DountChartConfig = {
	label_column: string
	value_column: string
}

export type TableChartConfig = {
	rows: string[]
	columns: string[]
	values: string[]
}

export type ChartConfig = AxisChartConfig | NumberChartConfig | DountChartConfig | TableChartConfig
