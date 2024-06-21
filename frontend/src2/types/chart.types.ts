export const AXIS_CHARTS = ['Bar', 'Line', 'Row']
export type AxisChartType = (typeof AXIS_CHARTS)[number]

export const CHARTS = ['Number', ...AXIS_CHARTS, 'Donut', 'Table']
export type ChartType = (typeof CHARTS)[number]

export type AxisChartConfig = {
	x_axis: string
	y_axis: string[]
	split_by: string
}

export type NumberChartConfig = {
	number_column: string
	comparison: boolean
	sparkline: boolean
	date_column?: string
	shorten_numbers?: boolean
	precision?: number
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
