import { graphic } from 'echarts/core'
import { formatNumber, getShortNumber } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { BarChartConfig, LineChartConfig } from '../types/chart.types'
import { ColumnDataType, QueryResultColumn, QueryResultRow } from '../types/query.types'
import { Chart } from './chart'
import { getColors } from './colors'

// eslint-disable-next-line no-unused-vars
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

export function getLineChartOptions(chart: Chart) {
	const _config = chart.doc.config as LineChartConfig
	const _columns = chart.dataQuery.result.columns
	const _rows = chart.dataQuery.result.rows

	const measures = _columns.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
	const show_legend = measures.length > 1

	const xAxis = getXAxis({ column_type: _config.x_axis.data_type })

	const leftYAxis = getYAxis()
	const rightYAxis = getYAxis({ is_secondary: true })
	const yAxis = !_config.y2_axis ? [leftYAxis] : [leftYAxis, rightYAxis]

	const sortedRows = FIELDTYPES.DATE.includes(_config.x_axis.data_type)
		? _rows.sort((a, b) => {
				const a_date = new Date(a[_config.x_axis.column_name])
				const b_date = new Date(b[_config.x_axis.column_name])
				return a_date.getTime() - b_date.getTime()
		  })
		: _rows

	const getSeriesData = (column: string) =>
		sortedRows.map((r) => {
			const x_value = r[_config.x_axis.column_name]
			const y_value = r[column]
			return [x_value, y_value]
		})

	const colors = getColors()

	return {
		animation: true,
		animationDuration: 700,
		grid: getGrid({ show_legend }),
		colors,
		xAxis,
		yAxis,
		series: measures.map((c, idx) => {
			const is_right_axis = _config.y2_axis?.some((y) => c.name.includes(y.measure_name))
			const type = is_right_axis ? _config.y2_axis_type : 'line'
			return {
				type,
				name: c.name,
				data: getSeriesData(c.name),
				emphasis: { focus: 'series' },
				yAxisIndex: is_right_axis ? 1 : 0,
				smooth: _config.smooth ? 0.4 : false,
				smoothMonotone: 'x',
				showSymbol: _config.show_data_points || _config.show_data_labels,
				label: {
					fontSize: 11,
					show: _config.show_data_labels,
					position: idx === measures.length - 1 ? 'top' : 'inside',
					formatter: (params: any) => {
						return getShortNumber(params.value?.[1], 1)
					},
				},
				labelLayout: { hideOverlap: true },
				areaStyle: _config.show_area
					? {
							color: new graphic.LinearGradient(0, 0, 0, 1, [
								{ offset: 0, color: colors[idx] },
								{ offset: 1, color: '#fff' },
							]),
							opacity: 0.2,
					  }
					: undefined,
			}
		}),
		tooltip: getTooltip(),
		legend: getLegend(show_legend),
	}
}

export function getBarChartOptions(chart: Chart) {
	const _config = chart.doc.config as BarChartConfig
	const _columns = chart.dataQuery.result.columns
	const _rows = chart.dataQuery.result.rows

	const measures = _columns.filter((c) => FIELDTYPES.MEASURE.includes(c.type))
	const total_per_x_value = _rows.reduce((acc, row) => {
		const x_value = row[_config.x_axis.column_name]
		if (!acc[x_value]) acc[x_value] = 0
		measures.forEach((m) => (acc[x_value] += row[m.name]))
		return acc
	}, {} as Record<string, number>)

	const show_legend = measures.length > 1

	const xAxisValues = _rows.map((r) => r[_config.x_axis.column_name])
	const xAxis = getXAxis({
		values: _config.swap_axes ? xAxisValues.reverse() : xAxisValues,
		column_type: _config.x_axis.data_type,
	})

	const leftYAxis = getYAxis({ normalized: _config.normalize })
	const rightYAxis = getYAxis({ is_secondary: true })
	const yAxis = !_config.y2_axis ? [leftYAxis] : [leftYAxis, rightYAxis]

	const getSeriesData = (column: string) =>
		_rows.map((r) => {
			const x_value = r[_config.x_axis.column_name]
			const y_value = r[column]
			if (!_config.normalize) {
				return _config.swap_axes ? [y_value, x_value] : [x_value, y_value]
			}

			const total = total_per_x_value[x_value]
			const normalized_value = total ? (y_value / total) * 100 : 0
			return _config.swap_axes ? [normalized_value, x_value] : [x_value, normalized_value]
		})

	const colors = getColors()

	return {
		animation: true,
		animationDuration: 700,
		colors: colors,
		grid: getGrid({ show_legend }),
		xAxis: _config.swap_axes ? yAxis : xAxis,
		yAxis: _config.swap_axes ? xAxis : yAxis,
		series: measures.map((c, idx) => {
			const is_right_axis = _config.y2_axis?.some((y) => c.name.includes(y.measure_name))
			const type = is_right_axis ? _config.y2_axis_type : 'bar'
			return getSeries({
				type,
				name: c.name,
				data: getSeriesData(c.name),
				stack: type === 'bar' && _config.stack,
				axis_swaped: _config.swap_axes,
				on_right_axis: is_right_axis,
				show_data_label: _config.show_data_labels,
				data_label_position: idx === measures.length - 1 ? 'top' : 'inside',
			})
		}),
		tooltip: getTooltip(),
		legend: getLegend(show_legend),
	}
}

type XAxisCustomizeOptions = {
	values?: string[]
	column_type?: ColumnDataType
}
function getXAxis(options: XAxisCustomizeOptions = {}) {
	const xAxisIsDate = options.column_type && FIELDTYPES.DATE.includes(options.column_type)
	return {
		type: xAxisIsDate ? 'time' : 'category',
		data: options.values,
		z: 2,
		scale: true,
		boundaryGap: ['1%', '2%'],
		splitLine: { show: false },
		axisLine: { show: true },
		axisTick: { show: false },
	}
}

type YAxisCustomizeOptions = {
	is_secondary?: boolean
	normalized?: boolean
}
function getYAxis(options: YAxisCustomizeOptions = {}) {
	return {
		show: true,
		type: 'value',
		z: 2,
		scale: false,
		alignTicks: true,
		boundaryGap: ['0%', '1%'],
		splitLine: { show: true },
		axisTick: { show: false },
		axisLine: { show: false, onZero: false },
		axisLabel: {
			show: true,
			hideOverlap: true,
			margin: 4,
			formatter: (value: number) => getShortNumber(value, 1),
		},
		min: options.normalized ? 0 : undefined,
		max: options.normalized ? 100 : undefined,
	}
}

type SeriesCustomizationOptions = {
	type?: 'bar' | 'line'
	data?: any[]
	name?: string
	stack?: boolean
	axis_swaped?: boolean
	show_data_label?: boolean
	data_label_position?: 'inside' | 'top'
	on_right_axis?: boolean
}
function getSeries(options: SeriesCustomizationOptions = {}) {
	return {
		type: options.type || 'bar',
		stack: options.stack,
		name: options.name,
		data: options.data,
		label: {
			show: options.show_data_label,
			position: options.axis_swaped ? 'right' : options.data_label_position,
			formatter: (params: any) => {
				const valueIndex = options.axis_swaped ? 0 : 1
				return getShortNumber(params.value?.[valueIndex], 1)
			},
			fontSize: 11,
		},
		labelLayout: { hideOverlap: true },
		emphasis: { focus: 'series' },
		barMaxWidth: 60,
		yAxisIndex: options.on_right_axis ? 1 : 0,
	}
}

export function getDonutChartOptions(columns: QueryResultColumn[], rows: QueryResultRow[]) {
	const MAX_SLICES = 10
	const data = getDonutChartData(columns, rows, MAX_SLICES)

	const colors = getColors()
	return {
		animation: true,
		animationDuration: 700,
		colors: colors,
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
		legend: getLegend(),
		tooltip: {
			...getTooltip(),
			trigger: 'item',
		},
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

function getGrid(options: any = {}) {
	return {
		top: 18,
		left: 30,
		right: 30,
		bottom: options.show_legend ? 36 : 22,
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

function getLegend(show_legend = true) {
	return {
		show: show_legend,
		icon: 'circle',
		type: 'scroll',
		orient: 'horizontal',
		bottom: 'bottom',
		itemGap: 16,
		padding: [10, 30],
		textStyle: { padding: [0, 0, 0, -4] },
		pageIconSize: 10,
		pageIconColor: '#64748B',
		pageIconInactiveColor: '#C0CCDA',
		pageFormatter: '{current}',
		pageButtonItemGap: 2,
	}
}
