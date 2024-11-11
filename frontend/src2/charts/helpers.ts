import { graphic } from 'echarts/core'
import { copy, ellipsis, formatNumber, getShortNumber, getUniqueId } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { column, getFormattedDate } from '../query/helpers'
import useQuery from '../query/query'
import {
	AxisChartConfig,
	BarChartConfig,
	ChartConfig,
	DountChartConfig,
	LineChartConfig,
	Series,
	SeriesLine,
} from '../types/chart.types'
import {
	ColumnDataType,
	FilterRule,
	GranularityType,
	Operation,
	QueryResult,
	QueryResultColumn,
	QueryResultRow,
} from '../types/query.types'
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

export function getLineChartOptions(config: LineChartConfig, result: QueryResult) {
	const _columns = result.columns
	const _rows = result.rows

	const number_columns = _columns.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
	const show_legend = number_columns.length > 1

	const xAxis = getXAxis({ column_type: config.x_axis.data_type })
	const xAxisIsDate = FIELDTYPES.DATE.includes(config.x_axis.data_type)
	const granularity = xAxisIsDate ? getGranularity(config.x_axis.dimension_name, config) : null

	const leftYAxis = getYAxis()
	const rightYAxis = getYAxis()
	const hasRightAxis = config.y_axis.series.some((s) => s.align === 'Right')
	const yAxis = !hasRightAxis ? [leftYAxis] : [leftYAxis, rightYAxis]

	const sortedRows = xAxisIsDate
		? _rows.sort((a, b) => {
				const a_date = new Date(a[config.x_axis.dimension_name])
				const b_date = new Date(b[config.x_axis.dimension_name])
				return a_date.getTime() - b_date.getTime()
		  })
		: _rows

	const getSeriesData = (column: string) =>
		sortedRows.map((r) => {
			const x_value = r[config.x_axis.dimension_name]
			const y_value = r[column]
			return [x_value, y_value]
		})

	const colors = getColors()

	return {
		animation: true,
		animationDuration: 700,
		grid: getGrid({ show_legend }),
		color: colors,
		xAxis,
		yAxis,
		series: number_columns.map((c, idx) => {
			const serie = getSerie(config, c.name) as SeriesLine

			const is_right_axis = serie.align === 'Right'
			const type = serie.type?.toLowerCase() || 'line'
			const smooth = serie.smooth ?? config.y_axis.smooth
			const show_data_points = serie.show_data_points ?? config.y_axis.show_data_points
			const show_area = serie.show_area ?? config.y_axis.show_area
			const show_data_labels = serie.show_data_labels ?? config.y_axis.show_data_labels
			const color = serie.color?.[0] || colors[idx]
			const name = config.split_by?.column_name ? c.name : serie.measure.measure_name || c.name

			return {
				type,
				name,
				data: getSeriesData(c.name),
				color: color,
				yAxisIndex: is_right_axis ? 1 : 0,
				smooth: smooth ? 0.4 : false,
				smoothMonotone: 'x',
				showSymbol: show_data_points || show_data_labels,
				label: {
					fontSize: 11,
					show: show_data_labels,
					position: idx === number_columns.length - 1 ? 'top' : 'inside',
					formatter: (params: any) => {
						return getShortNumber(params.value?.[1], 1)
					},
				},
				labelLayout: { hideOverlap: true },
				itemStyle: { color: color },
				areaStyle: show_area ? getAreaStyle(color) : undefined,
			}
		}),
		tooltip: getTooltip({
			xAxisIsDate,
			granularity,
		}),
		legend: getLegend(show_legend),
	}
}

function getAreaStyle(color: string) {
	return {
		color: new graphic.LinearGradient(0, 0, 0, 1, [
			{ offset: 0, color: color },
			{ offset: 1, color: '#fff' },
		]),
		opacity: 0.2,
	}
}

export function getBarChartOptions(config: BarChartConfig, result: QueryResult, swapAxes = false) {
	const _columns = result.columns
	const _rows = result.rows

	const number_columns = _columns.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
	const show_legend = number_columns.length > 1

	const xAxis = getXAxis({ column_type: config.x_axis.data_type })
	const xAxisIsDate = FIELDTYPES.DATE.includes(config.x_axis.data_type)
	const granularity = xAxisIsDate ? getGranularity(config.x_axis.dimension_name, config) : null

	const leftYAxis = getYAxis({ normalized: config.y_axis.normalize })
	const rightYAxis = getYAxis({ normalized: config.y_axis.normalize })
	const hasRightAxis = config.y_axis.series.some((s) => s.align === 'Right')
	const yAxis = !hasRightAxis ? [leftYAxis] : [leftYAxis, rightYAxis]

	const sortedRows = xAxisIsDate
		? _rows.sort((a, b) => {
				const a_date = new Date(a[config.x_axis.dimension_name])
				const b_date = new Date(b[config.x_axis.dimension_name])
				return a_date.getTime() - b_date.getTime()
		  })
		: _rows

	const total_per_x_value = _rows.reduce((acc, row) => {
		const x_value = row[config.x_axis.dimension_name]
		if (!acc[x_value]) acc[x_value] = 0
		number_columns.forEach((m) => (acc[x_value] += row[m.name]))
		return acc
	}, {} as Record<string, number>)

	const getSeriesData = (column: string) =>
		sortedRows
			.map((r) => {
				const x_value = r[config.x_axis.dimension_name]
				const y_value = r[column]
				const normalize = config.y_axis.normalize
				if (!normalize) {
					return [x_value, y_value]
				}

				const total = total_per_x_value[x_value]
				const normalized_value = total ? (y_value / total) * 100 : 0
				return [x_value, normalized_value]
			})
			.map((d) => (swapAxes ? [d[1], d[0]] : d))

	const colors = getColors()

	return {
		animation: true,
		animationDuration: 700,
		color: colors,
		grid: getGrid({ show_legend }),
		xAxis: swapAxes ? yAxis : xAxis,
		yAxis: swapAxes ? xAxis : yAxis,
		series: number_columns.map((c, idx) => {
			const serie = getSerie(config, c.name)
			const is_right_axis = serie.align === 'Right'

			const color = serie.color?.[0] || colors[idx]
			const type = serie.type?.toLowerCase() || 'bar'
			const stack = type === 'bar' && config.y_axis.stack ? 'stack' : undefined
			const show_data_labels = serie.show_data_labels ?? config.y_axis.show_data_labels

			const data = getSeriesData(c.name)
			const name = config.split_by?.column_name ? c.name : serie.measure.measure_name || c.name

			return {
				type,
				stack,
				name,
				data: swapAxes ? data.reverse() : data,
				color: color,
				label: {
					show: show_data_labels,
					position: idx === number_columns.length - 1 ? (swapAxes ? 'right' : 'top') : 'inside',
					formatter: (params: any) => {
						const _val = swapAxes ? params.value?.[0] : params.value?.[1]
						return getShortNumber(_val, 1)
					},
					fontSize: 11,
				},
				labelLayout: { hideOverlap: true },
				barMaxWidth: 60,
				yAxisIndex: is_right_axis ? 1 : 0,
				itemStyle: { color: color },
			}
		}),
		tooltip: getTooltip({
			xAxisIsDate,
			granularity,
			xySwapped: swapAxes,
		}),
		legend: getLegend(show_legend),
	}
}

function getSerie(config: AxisChartConfig, number_column: string): Series {
	let serie
	if (!config.split_by?.column_name) {
		serie = config.y_axis.series.find((s) => s.measure.measure_name === number_column)
	} else {
		let seriesCount = config.y_axis.series.filter((s) => s.measure.measure_name).length
		if (seriesCount === 1) {
			serie = config.y_axis.series[0]
		} else {
			serie = config.y_axis.series.find((s) => number_column.includes(s.measure.measure_name))
		}
	}

	return (
		serie ||
		({
			measure: {
				measure_name: number_column,
			},
		} as Series)
	)
}

type XAxisCustomizeOptions = {
	column_type?: ColumnDataType
}
function getXAxis(options: XAxisCustomizeOptions = {}) {
	const xAxisIsDate = options.column_type && FIELDTYPES.DATE.includes(options.column_type)
	return {
		type: xAxisIsDate ? 'time' : 'category',
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

export function getDonutChartOptions(config: DountChartConfig, result: QueryResult) {
	const columns = result.columns
	const rows = result.rows

	const MAX_SLICES = 10
	const valueColumn = columns.find((c) => FIELDTYPES.MEASURE.includes(c.type))
	const data = getDonutChartData(columns, rows, MAX_SLICES)
	const labels = data.map((d) => d[0])
	const values = data.map((d) => d[1])
	const total = values.reduce((a, b) => a + b, 0)

	const colors = getColors()

	let center, radius, top, left, right, bottom, padding, orient
	const legend_position = config.legend_position || 'bottom'
	if (legend_position == 'bottom') {
		orient = 'horizontal'
		radius = ['45%', '75%']
		center = ['50%', '45%']
		bottom = 0
		left = 'center'
		padding = [30, 30, 10, 30]
	}
	if (legend_position == 'top') {
		orient = 'horizontal'
		radius = ['45%', '75%']
		center = ['50%', '55%']
		top = 0
		left = 'center'
		padding = 20
	}
	if (legend_position == 'right') {
		orient = 'vertical'
		radius = ['45%', '80%']
		center = ['33%', '50%']
		left = '63%'
		top = 'middle'
		padding = [30, 0, 30, 0]
	}
	if (legend_position == 'left') {
		orient = 'vertical'
		radius = ['45%', '80%']
		center = ['67%', '50%']
		right = '63%'
		top = 'middle'
		padding = [30, 0, 30, 0]
	}

	return {
		animation: true,
		animationDuration: 700,
		color: colors,
		dataset: { source: data },
		series: [
			{
				type: 'pie',
				name: valueColumn?.name,
				center,
				radius,
				labelLine: { show: false },
				label: { show: false },
				emphasis: { scaleSize: 5 },
			},
		],
		legend: {
			...getLegend(),
			top,
			left,
			right,
			bottom,
			padding,
			orient,
			formatter: (name: string) => {
				const labelIndex = labels.indexOf(name)
				const percent = (values[labelIndex] / total) * 100
				return `${ellipsis(name, 20)} (${percent.toFixed(0)}%)`
			},
		},
		tooltip: {
			trigger: 'item',
			confine: true,
			appendToBody: false,
			valueFormatter: (value: number) => {
				const percent = (value / total) * 100
				return `${formatNumber(value, 2)} (${percent.toFixed(0)}%)`
			},
		},
	}
}

function getDonutChartData(
	columns: QueryResultColumn[],
	rows: QueryResultRow[],
	maxSlices: number
) {
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

export function getFunnelChartOptions(config: DountChartConfig, result: QueryResult) {
	const rows = result.rows

	const labelColumn = config.label_column.dimension_name
	const valueColumn = config.value_column.measure_name
	const labels = rows.map((r) => r[labelColumn])
	const values = rows.map((r) => r[valueColumn])

	const colors = getColors()

	return {
		animation: true,
		animationDuration: 300,
		color: colors,
		series: [
			{
				name: 'Funnel',
				type: 'funnel',
				orient: 'vertical',
				funnelAlign: 'center',
				top: 'center',
				left: 'center',
				width: '60%',
				height: '80%',
				minSize: '10px',
				maxSize: '100%',
				sort: 'descending',
				label: {
					show: true,
					position: 'inside',
					formatter: (params: any) => {
						const index = labels.indexOf(params.name)
						const percent = ((values[index] / values[0]) * 100).toFixed(0)
						return `${params.name} (${percent}%)`
					},
				},
				gap: 6,
				data: values.map((value, index) => ({
					name: labels[index],
					value: value,
					itemStyle: {
						color: colors[index],
						borderColor: colors[index],
						borderWidth: 4,
						borderCap: 'round',
						borderJoin: 'round',
					},
					emphasis: {
						itemStyle: {
							color: colors[index],
							borderColor: colors[index],
							borderWidth: 6,
							borderCap: 'round',
							borderJoin: 'round',
						},
					},
				})),
			},
		],
	}
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

function getTooltip(options: any = {}) {
	return {
		trigger: 'axis',
		confine: true,
		appendToBody: false,
		formatter: (params: Object | Array<Object>) => {
			if (!Array.isArray(params)) {
				const p = params as any
				const value = options.xySwapped ? p.value[0] : p.value[1]
				const formatted = isNaN(value) ? value : formatNumber(value)
				return `
					<div class="flex items-center justify-between gap-5">
						<div>${p.name}</div>
						<div class="font-bold">${formatted}</div>
					</div>
				`
			}
			if (Array.isArray(params)) {
				const t = params.map((p, idx) => {
					const xValue = options.xySwapped ? p.value[1] : p.value[0]
					const yValue = options.xySwapped ? p.value[0] : p.value[1]
					const formattedX =
						options.xAxisIsDate && options.granularity
							? getFormattedDate(xValue, options.granularity)
							: xValue
					const formattedY = isNaN(yValue) ? yValue : formatNumber(yValue)
					return `
							<div class="flex flex-col">
								${idx == 0 ? `<div>${formattedX}</div>` : ''}
								<div class="flex items-center justify-between gap-5">
									<div class="flex gap-1 items-center">
										${p.marker}
										<div>${p.seriesName}</div>
									</div>
									<div class="font-bold">${formattedY}</div>
								</div>
							</div>
						`
				})
				return t.join('')
			}
		},
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

export function getDrillDownQuery(
	operations: Operation[],
	result: QueryResult,
	row: QueryResultRow,
	col: QueryResultColumn,
	use_live_connection = true
) {
	if (!result.columns?.length || !row || !col) return

	if (!FIELDTYPES.NUMBER.includes(col.type)) {
		return
	}

	const textColumns = result.columns
		.filter((column) => FIELDTYPES.TEXT.includes(column.type))
		.map((column) => column.name)

	const dateColumns = result.columns
		.filter((column) => FIELDTYPES.DATE.includes(column.type))
		.map((column) => column.name)

	const rowIndex = result.formattedRows.findIndex((r) => r === row)
	const currRow = result.rows[rowIndex]
	const nextRow = result.rows[rowIndex + 1]

	const filters: FilterRule[] = []
	for (const column_name of textColumns) {
		filters.push({
			column: column(column_name),
			operator: '=',
			value: currRow[column_name] as string,
		})
	}

	for (const column_name of dateColumns) {
		if (nextRow) {
			filters.push({
				column: column(column_name),
				operator: '>=',
				value: currRow[column_name] as string,
			})
			filters.push({
				column: column(column_name),
				operator: '<',
				value: nextRow[column_name] as string,
			})
		} else {
			filters.push({
				column: column(column_name),
				operator: '>=',
				value: currRow[column_name] as string,
			})
		}
	}

	const query = useQuery({ name: getUniqueId(), operations: [] })
	query.autoExecute = false
	query.doc.use_live_connection = use_live_connection

	query.setOperations(copy(operations))
	const summarizeIndex = query.doc.operations.findIndex((op) => op.type === 'summarize')
	query.doc.operations.splice(summarizeIndex)

	query.addFilterGroup({
		logical_operator: 'And',
		filters: filters,
	})

	return query
}

export function handleOldYAxisConfig(old_y_axis: any): AxisChartConfig['y_axis'] {
	if (Array.isArray(old_y_axis)) {
		return {
			series: old_y_axis.map((measure: any) => ({ measure })),
		}
	}
	return old_y_axis
}

export function setDimensionNames(config: any) {
	const setDimensionName = (dimension: any) => {
		if (
			dimension &&
			typeof dimension === 'object' &&
			!dimension.dimension_name &&
			dimension.column_name
		) {
			dimension.dimension_name = dimension.column_name
		}
		return dimension
	}

	const dimensionPaths = ['x_axis', 'split_by', 'date_column', 'label_column']
	dimensionPaths.forEach((path) => {
		config[path] = setDimensionName(config[path])
	})
	if (config.rows && config.rows.length) {
		config.rows = config.rows.map(setDimensionName)
	}
	if (config.columns && config.columns.length) {
		config.columns = config.columns.map(setDimensionName)
	}
	return config
}

export function getGranularity(dimension_name: string, config: ChartConfig) {
	const column = Object.entries(config).find(([_, value]) => {
		if (!value) return false
		if (Array.isArray(value)) {
			return value.some((v) => v.dimension_name === dimension_name)
		}
		if (typeof value === 'object') {
			return value.dimension_name === dimension_name
		}
		return false
	})
	if (!column) return

	if (Array.isArray(column[1])) {
		const granularity = column[1].find((v) => v.dimension_name === dimension_name)?.granularity
		return granularity as GranularityType
	}

	const granularity = column[1].granularity
	return granularity as GranularityType
}
