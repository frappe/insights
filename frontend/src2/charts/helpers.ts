import { FIELDTYPES, formatNumber, getShortNumber } from '@/utils'

export const AXIS_CHARTS = ['Bar', 'Line', 'Row'] //, 'Scatter', 'Area']
export type AxisChartType = (typeof AXIS_CHARTS)[number]

export const CHARTS = ['Metric', ...AXIS_CHARTS, 'Donut', 'Table'] // 'Funnel',
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

export type DountChartConfig = {
	label_column: string
	value_column: string
}

export type TableChartConfig = {
	rows: string[]
	columns: string[]
	values: string[]
}

export type ChartConfig = AxisChartConfig | MetricChartConfig | DountChartConfig | TableChartConfig

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

export function getLineChartOptions(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	const data = getData(columns, rows)
	return {
		animation: true,
		grid: getGrid(),
		dataset: { source: data },
		xAxis: { type: 'category' },
		yAxis: {
			type: 'value',
			splitLine: { lineStyle: { type: 'dashed' } },
			axisLabel: { formatter: (value: Number) => getShortNumber(value, 1) },
		},
		series: columns
			.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
			.map((c) => ({ type: 'line' })),
		tooltip: getTooltip(),
		legend: getLegend(),
	}
}

export function getRowChartOptions(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	const data = getData(columns, rows.reverse())
	return {
		animation: true,
		grid: getGrid(),
		dataset: { source: data },
		xAxis: { type: 'value' },
		yAxis: { type: 'category' },
		series: columns
			.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
			.map((c) => ({ type: 'bar', stack: 'stack' })),
		tooltip: getTooltip(),
		legend: getLegend(),
	}
}

export function getBarChartOptions(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	const data = getData(columns, rows)
	return {
		animation: true,
		grid: getGrid(),
		dataset: { source: data },
		xAxis: { type: 'category' },
		yAxis: {
			type: 'value',
			splitLine: { lineStyle: { type: 'dashed' } },
			axisLabel: { formatter: (value: Number) => getShortNumber(value, 1) },
		},
		series: columns
			.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
			.map((c) => ({ type: 'bar', stack: 'stack' })),
		tooltip: getTooltip(),
		legend: getLegend(),
	}
}

export function getDonutChartOptions(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	const MAX_SLICES = 10
	const data = getDonutChartData(columns, rows, MAX_SLICES)
	return {
		animation: true,
		dataset: { source: data },
		series: [
			{
				type: 'pie',
				center: ['50%', '45%'],
				radius: ['40%', '70%'],
				labelLine: { show: false },
				label: { show: false },
				emphasis: {
					scaleSize: 5,
				},
			},
		],
		tooltip: getTooltip(),
		legend: getLegend(),
	}
}

function getDonutChartData(
	columns: QueryResultColumn[],
	rows: QueryResultRow[],
	maxSlices: number
) {
	// reduce the number of slices to 10
	const measureColumn = columns.find((c) => FIELDTYPES.MEASURE.includes(c.type))
	if (!measureColumn) {
		throw new Error('No measure column found')
	}

	const labelColumn = columns.find((c) => FIELDTYPES.DIMENSION.includes(c.type))
	if (!labelColumn) {
		throw new Error('No label column found')
	}

	const valueByLabel = rows.reduce((acc, row) => {
		const label = row[labelColumn.name]
		const value = row[measureColumn.name]
		if (!acc[label]) acc[label] = 0
		acc[label] = acc[label] + value
		return acc
	}, {} as Record<string, number>)

	const sortedLabels = Object.keys(valueByLabel).sort((a, b) => valueByLabel[b] - valueByLabel[a])
	const topLabels = sortedLabels.slice(0, maxSlices)
	const others = sortedLabels.slice(maxSlices)
	const topData = topLabels.map((label) => [label, valueByLabel[label]])
	const othersTotal = others.reduce((acc, label) => acc + valueByLabel[label], 0)

	if (othersTotal) {
		topData.push(['Others', othersTotal])
	}

	return topData
}

function getData(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	type RowKey = keyof QueryResultRow
	const columnNames = columns.map((c) => c.name) as RowKey[]
	return [columnNames, ...rows.map((r) => columnNames.map((c) => r[c]))]
}

function getGrid() {
	return {
		top: 10,
		bottom: 35,
		left: 10,
		right: 10,
		containLabel: true,
	}
}

function getTooltip() {
	return {
		trigger: 'axis',
		confine: true,
		appendToBody: false,
		valueFormatter: (value: any) => (isNaN(value) ? value : formatNumber(value)),
	}
}

function getLegend() {
	return {
		icon: 'circle',
		type: 'scroll',
		orient: 'horizontal',
		bottom: 'bottom',
		pageIconSize: 12,
		pageIconColor: '#64748B',
		pageIconInactiveColor: '#C0CCDA',
		pageFormatter: '{current}',
		pageButtonItemGap: 2,
	}
}
