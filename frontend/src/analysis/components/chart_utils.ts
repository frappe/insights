import { QueryResultColumn, QueryResultRow } from '@/query/next/useQuery'
import { FIELDTYPES, formatNumber, getShortNumber } from '@/utils'

export const AXIS_CHARTS = ['Bar', 'Line', 'Row', 'Scatter', 'Area']
export type AxisChartType = (typeof AXIS_CHARTS)[number]

export const CHARTS = [...AXIS_CHARTS, 'Donut', 'Funnel', 'Table', 'Metric']
export type ChartType = (typeof CHARTS)[number]

export type AxisChartConfig = {
	x_axis: string
	y_axis: string[]
	split_by: string
}

export type MetricChartConfig = {
	metric_column: string
	target_value?: number
	target_column?: string
	date_column?: string
	shorten_numbers?: boolean
	precision?: number
	prefix?: string
	suffix?: string
}

export type ChartConfig = AxisChartConfig | MetricChartConfig

export function guessChart(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	// categorize the columns into dimensions and measures and then into discrete and continuous
	const dimensions = columns.filter((c) => FIELDTYPES.DIMENSION.includes(c.type))
	const discreteDimensions = dimensions.filter((c) => FIELDTYPES.DISCRETE.includes(c.type))
	const continuousDimensions = dimensions.filter((c) => FIELDTYPES.CONTINUOUS.includes(c.type))

	const measures = columns.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
	const discreteMeasures = measures.filter((c) => FIELDTYPES.DISCRETE.includes(c.type))
	const continuousMeasures = measures.filter((c) => FIELDTYPES.CONTINUOUS.includes(c.type))

	if (measures.length === 1 && dimensions.length === 0) return 'number'
	if (discreteDimensions.length === 1 && measures.length) return 'bar'
	if (continuousDimensions.length === 1 && measures.length) return 'line'
	if (discreteDimensions.length > 1 && measures.length) return 'table'
}

export function getLineOrBarChartOptions(
	columns: QueryResultColumn[],
	rows: QueryResultRow[],
	lineOrBar = 'bar'
) {
	const columnNames = columns.map((c) => c.name)
	const data = [
		columns.map((c) => c.name),
		...rows.map((r) => columnNames.map((c) => r[c as keyof QueryResultRow])),
	]
	const maxColumnLabelLength = Math.max(
		...columns.filter((c) => FIELDTYPES.MEASURE.includes(c.type)).map((c) => c.name.length)
	)
	const rightOffset = maxColumnLabelLength * 15
	return {
		grid: {
			top: 10,
			left: 10,
			right: rightOffset,
			bottom: 10,
			containLabel: true,
		},
		dataset: { source: data },
		xAxis: { type: 'category' },
		yAxis: {
			type: 'value',
			splitLine: { lineStyle: { type: 'dashed' } },
			axisLabel: { formatter: (value: Number) => getShortNumber(value, 1) },
		},
		series: columns
			.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
			.map((c) => ({ type: lineOrBar, stack: 'stack' })),
		tooltip: {
			trigger: 'axis',
			confine: true,
			appendToBody: false,
			valueFormatter: (value: any) => (isNaN(value) ? value : formatNumber(value)),
		},
		legend: {
			icon: 'circle',
			right: 0,
			orient: 'vertical',
			top: 'top',
		},
	}
}
