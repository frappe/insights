import { graphic } from 'echarts/core'
import { ellipsis, formatNumber, getShortNumber, toTitleCase } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { getFormattedDate } from '../query/helpers'
import {
	AxisChartConfig,
	BarChartConfig,
	ChartConfig,
	DonutChartConfig,
	FunnelChartConfig,
	LineChartConfig,
	MapChartConfig,
	BubbleChartConfig,
	Series,
	SeriesLine,
	XAxis,
} from '../types/chart.types'
import { QueryResult, QueryResultColumn, QueryResultRow } from '../types/query.types'
import { getColors, getGradientColors } from './colors'

interface GeoJSONFeature {
	type: string
	id?: string
	properties?: {
		NAME_2?: string
		[key: string]: any
	}
	geometry: any
}

interface GeoJSONData {
	type: string
	features: GeoJSONFeature[]
}

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
	const show_scrollbar = config.y_axis.show_scrollbar || false

	const xAxis = getXAxis(config.x_axis)
	const xAxisIsDate = FIELDTYPES.DATE.includes(config.x_axis.dimension.data_type)
	const granularity = xAxisIsDate
		? getGranularity(config.x_axis.dimension.dimension_name, config)
		: null

	const leftYAxis = getYAxis({ min: config.y_axis.min, max: config.y_axis.max })
	const rightYAxis = getYAxis()
	const hasRightAxis = config.y_axis.series.some((s) => s.align === 'Right')
	const yAxis = !hasRightAxis ? [leftYAxis] : [leftYAxis, rightYAxis]

	const sortedRows = xAxisIsDate
		? [..._rows].sort((a, b) => {
				const a_date = new Date(a[config.x_axis.dimension.dimension_name])
				const b_date = new Date(b[config.x_axis.dimension.dimension_name])
				return a_date.getTime() - b_date.getTime()
		  })
		: _rows

	const getSeriesData = (column: string) =>
		sortedRows.map((r) => {
			const x_value = r[config.x_axis.dimension.dimension_name]
			const y_value = r[column]
			return [x_value, y_value]
		})

	const colors = getColors()

	return {
		animation: true,
		animationDuration: 700,
		dataZoom: getDataZoom(show_scrollbar),
		grid: getGrid({ show_legend, show_scrollbar }),
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
			const name = config.split_by?.dimension?.column_name ? c.name : serie.measure.measure_name || c.name

			let labelPosition = 'top'
			if (type === 'bar') {
				labelPosition = 'inside'
			}

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
					position: labelPosition,
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
		legend: getLegend(show_legend, show_scrollbar),
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

function getDataZoom(show: boolean, swapAxes = false) {
	return {
		show,
		orient: swapAxes ? 'vertical' : 'horizontal',
		type: 'slider',
		zoomLock: false,
		bottom: swapAxes ? "20%" : "4%",
		height: swapAxes ? "80%" : 15,
		width: swapAxes ? 15 : "90%",
		left: swapAxes ? null : "5%",
		right: swapAxes ? 10 : null,
		handleSize: 25,
	}
}

export function getBarChartOptions(config: BarChartConfig, result: QueryResult, swapAxes = false) {
	const _columns = result.columns
	const _rows = result.rows

	const number_columns = _columns.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
	const show_legend = number_columns.length > 1
	const show_scrollbar = config.y_axis.show_scrollbar || false

	const xAxis = getXAxis(config.x_axis)
	const xAxisIsDate = FIELDTYPES.DATE.includes(config.x_axis.dimension.data_type)
	const granularity = xAxisIsDate
		? getGranularity(config.x_axis.dimension.dimension_name, config)
		: null

	const leftYAxis = getYAxis({
		normalized: config.y_axis.normalize,
		min: config.y_axis.min,
		max: config.y_axis.max,
	})
	const rightYAxis = getYAxis({ normalized: config.y_axis.normalize })
	const hasRightAxis = config.y_axis.series.some((s) => s.align === 'Right')
	const yAxis = !hasRightAxis ? [leftYAxis] : [leftYAxis, rightYAxis]

	const sortedRows = xAxisIsDate
		? [..._rows].sort((a, b) => {
				const a_date = new Date(a[config.x_axis.dimension.dimension_name])
				const b_date = new Date(b[config.x_axis.dimension.dimension_name])
				return a_date.getTime() - b_date.getTime()
		  })
		: _rows

	const total_per_x_value = _rows.reduce((acc, row) => {
		const x_value = row[config.x_axis.dimension.dimension_name]
		if (!acc[x_value]) acc[x_value] = 0
		number_columns.forEach((m) => (acc[x_value] += row[m.name]))
		return acc
	}, {} as Record<string, number>)

	const getSeriesData = (column: string) =>
		sortedRows
			.map((r) => {
				const x_value = r[config.x_axis.dimension.dimension_name]
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
		grid: getGrid({ show_legend, show_scrollbar, swapAxes }),
		xAxis: swapAxes ? yAxis : xAxis,
		yAxis: swapAxes ? xAxis : yAxis,
		dataZoom: getDataZoom(show_scrollbar, swapAxes),
		series: number_columns.map((c, idx) => {
			const serie = getSerie(config, c.name)
			const is_right_axis = serie.align === 'Right'

			const color = serie.color?.[0] || colors[idx]
			const type = serie.type?.toLowerCase() || 'bar'
			const stack = type === 'bar' && config.y_axis.stack ? 'stack' : undefined
			const show_data_labels = serie.show_data_labels ?? config.y_axis.show_data_labels
			const data = getSeriesData(c.name)
			const name = config.split_by?.dimension?.column_name ? c.name : serie.measure.measure_name || c.name

			const roundedCorners = swapAxes ? [0, 2, 2, 0] : [2, 2, 0, 0]
			const isLast = idx === number_columns.length - 1

			let labelPosition = 'inside'
			if (type == 'line') {
				labelPosition = 'top'
			}

			return {
				type,
				stack: config.y_axis.overlap ? undefined : stack,
				name,
				data: swapAxes ? data.reverse() : data,
				color: color,
				label: {
					show: show_data_labels,
					position: labelPosition,
					formatter: (params: any) => {
						const _val = swapAxes ? params.value?.[0] : params.value?.[1]
						return getShortNumber(_val, 1)
					},
					fontSize: 11,
				},
				barGap: config.y_axis.overlap ? '-100%' : undefined,
				labelLayout: { hideOverlap: true },
				yAxisIndex: is_right_axis ? 1 : 0,
				itemStyle: {
					color: color,
					borderRadius: roundedCorners,
				},
			}
		}),
		tooltip: getTooltip({
			xAxisIsDate,
			granularity,
			xySwapped: swapAxes,
		}),
		legend: getLegend(show_legend, show_scrollbar, swapAxes),
	}
}

function getSerie(config: AxisChartConfig, number_column: string): Series {
	let serie
	if (!config.split_by?.dimension?.column_name) {
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

function getXAxis(x_axis: XAxis) {
	const columnType = x_axis.dimension.data_type
	const xAxisIsDate = columnType && FIELDTYPES.DATE.includes(columnType)
	const rotation = Math.min(Math.max(x_axis.label_rotation || 0, 0), 90)

	return {
		type: xAxisIsDate ? 'time' : 'category',
		z: 2,
		scale: true,
		alignTicks: true,
		boundaryGap: ['1%', '1%'],
		splitLine: { show: false },
		axisLine: { show: true, onZero: true },
		axisTick: { show: true },
		axisLabel: {
			show: true,
			rotate: rotation,
			width: 100,
			overflow: 'truncate',
			ellipsis: '...',
		},
	}
}

type YAxisCustomizeOptions = {
	is_secondary?: boolean
	normalized?: boolean
	min?: number
	max?: number
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
		axisTick: { show: true },
		axisLine: { show: true, onZero: true },
		axisLabel: {
			show: true,
			hideOverlap: true,
			margin: 8,
			formatter: (value: number) => getShortNumber(value, 1),
		},
		min: options.normalized ? 0 : options.min || undefined,
		max: options.normalized ? 100 : options.max || undefined,
	}
}

export function getDonutChartOptions(config: DonutChartConfig, result: QueryResult) {
	const columns = result.columns
	const rows = result.rows

	const valueColumn = columns.find((c) => FIELDTYPES.MEASURE.includes(c.type))
	const data = getDonutChartData(columns, rows, config.max_slices || 10)
	const labels = data.map((d) => d[0])
	const values = data.map((d) => d[1])
	const total = values.reduce((a, b) => a + b, 0)

	const colors = getColors()

	let center, radius, top, left, right, bottom, padding, orient
	const legend_position = config.legend_position || 'bottom'
	const show_inline_labels = config.show_inline_labels || false

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

	if (show_inline_labels) {
		center = ['50%', '50%']
		radius = ['45%', '75%']
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
				labelLine: {
					show: show_inline_labels,
					lineStyle: {
						width: 2,
					},
					length: 10,
					length2: 20,
					smooth: true,
				},
				label: {
					show: show_inline_labels,
					formatter: ({ value, name }: any) => {
						const percentage = total > 0 ? (value[1] / total) * 100 : 0
						return `${ellipsis(name, 20)} (${percentage.toFixed(0)}%)`
					},
				},
				emphasis: { scaleSize: 5 },
			},
		],
		legend: !show_inline_labels
			? {
					...getLegend(),
					top,
					left,
					right,
					bottom,
					padding,
					orient,
					formatter: (name: string) => {
						const labelIndex = labels.indexOf(name)
						const percentage = total > 0 ? (values[labelIndex] / total) * 100 : 0
						return `${ellipsis(name, 20)} (${percentage.toFixed(0)}%)`
					},
			  }
			: {
					show: false,
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

export function getFunnelChartOptions(config: FunnelChartConfig, result: QueryResult) {
	const rows = result.rows

	const labelColumn = config.label_column.dimension_name
	const valueColumn = config.value_column.measure_name
	const labelPosition = config.label_position || 'left'

	const labels = rows.map((r) => r[labelColumn])
	const values = rows.map((r) => r[valueColumn])

	let colors = getGradientColors('blue')

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
				width: '55%',
				height: '75%',
				minSize: '10px',
				maxSize: '100%',
				sort: 'descending',
				label: {
					show: true,
					// position doesn't have any effect
					// it is mapped here to re-render when the label position changes
					// because the label layout function is not changing when the label position changes
					// and so the chart doesn't re-render
					position: labelPosition,
					color: '#565656',
					lineHeight: 16,
					padding: [0, 5, 0, 0],
					formatter: (params: any) => {
						const index = labels.indexOf(params.name)
						const percentage = Number((values[index] / values[0]) * 100).toFixed(0)
						const value = getShortNumber(values[index], 2)
						return `${params.name}\n${value} (${percentage}%)`
					},
				},
				labelLine: { show: false },
				labelLayout(params: any) {
					const leftPos = params.rect.x - 15
					const rightPos = params.rect.x + params.rect.width + 15

					if (labelPosition === 'left') {
						return {
							x: leftPos,
							align: 'right',
						}
					}
					if (labelPosition === 'right') {
						return {
							x: rightPos,
							align: 'left',
						}
					}
					if (labelPosition === 'alternate') {
						return {
							x: params.dataIndex % 2 === 0 ? leftPos : rightPos,
							align: params.dataIndex % 2 === 0 ? 'right' : 'left',
						}
					}
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

function getMapChartData(
	columns: QueryResultColumn[],
	rows: QueryResultRow[],
	config?: MapChartConfig
) {
	const measureColumn = columns.find((c) => FIELDTYPES.MEASURE.includes(c.type))
	if (!measureColumn) {
		throw new Error('No measure column found')
	}

	const locationColumn = columns.find((c) => FIELDTYPES.DIMENSION.includes(c.type))
	if (!locationColumn) {
		throw new Error('No location column found')
	}

	// Get region mappings from config
	const regionMappings = config?.region_mappings?.[config.map_type || 'world'] || {}

	let aggregationColumn = locationColumn
	const locationValueMap = new Map<string, number>()

	for (const row of rows) {
		const rawLocation = row[aggregationColumn.name]
		const mappedLocation = regionMappings[rawLocation] || toTitleCase(rawLocation)
		const value = row[measureColumn.name]

		const currentValue = locationValueMap.get(mappedLocation) || 0
		locationValueMap.set(mappedLocation, currentValue + value)
	}

	const data = Array.from(locationValueMap.entries())
		.sort((a, b) => b[1] - a[1])
		.map(([location, value]) => [location, value])

	return data
}

function jenksMatrices(data: number[], nClasses: number) {

	//initialize matrices
	const mat1 = Array.from({ length: data.length + 1 }, () => Array(nClasses + 1).fill(0));
	const mat2 = Array.from({ length: data.length + 1 }, () => Array(nClasses + 1).fill(0));

	for (let i = 1; i <= nClasses; i++) {
	  mat1[1][i] = 1;
	  mat2[1][i] = 0;
	  for (let j = 2; j <= data.length; j++) mat2[j][i] = Infinity;
	}
	return { mat1, mat2 };
  }

function jenksBreaks(data: number[], nClasses: number, mat1: number[][], mat2: number[][]) {

	for (let l = 2; l <= data.length; l++) {
	  let s1 = 0, s2 = 0, w = 0;
	  for (let m = 1; m <= l; m++) {
		const i3 = l - m + 1;
		const val = data[i3 - 1];
		s2 += val * val;
		s1 += val;
		w++;
		const v = s2 - (s1 * s1) / w;
		const i4 = i3 - 1;
		if (i4 !== 0) {
		  for (let j = 2; j <= nClasses; j++) {
			if (mat2[l][j] >= v + mat2[i4][j - 1]) {
			  mat1[l][j] = i3;
			  mat2[l][j] = v + mat2[i4][j - 1];
			}
		  }
		}
	  }

	  mat1[l][1] = 1;
	  mat2[l][1] = s2 - (s1 * s1) / w;
	}
  }

function jenks(data: number[], nClasses: number) {

	data = data.slice().sort((a, b) => a - b);
	const { mat1, mat2 } = jenksMatrices(data, nClasses);

	jenksBreaks(data, nClasses, mat1, mat2);

	const kClass = Array(nClasses + 1).fill(0);
	kClass[nClasses] = data[data.length - 1];
	let k = data.length, countNum = nClasses;
	while (countNum >= 2) {
	  const idx = mat1[k][countNum] - 2;
	  kClass[countNum - 1] = data[idx];
	  k = mat1[k][countNum] - 1;
	  countNum--;
	}
	kClass[0] = data[0];
	return kClass;
  }

// visual map pieces
function mapPieces(values: number[]) {
	if (values.length === 0) {
		return [{ min: 0, max: 0, label: '0' }]
	}

	const validValues = values.filter(v => typeof v === 'number' && !isNaN(v) && v > 0)

	if (validValues.length === 0) {
		return [{ min: 0, max: 0, label: '0' }]
	}

	if (validValues.length === 1) {
		return [{
			min: 0,
			max: validValues[0],
			label: getShortNumber(validValues[0], 1)
		}]
	}

	const sortedValues = validValues.sort((a, b) => a - b)
	const uniqueValues = [...new Set(sortedValues)]
	const numClasses = Math.min(5, uniqueValues.length)

	const breaks = jenks(uniqueValues, numClasses)

	const pieces = []

	// create pieces from the breaks
	for (let i = 0; i < breaks.length - 1; i++) {
		const rangeMax = breaks[i + 1]
		const rangeMin = i === 0 ? 0 : breaks[i]

			pieces.push({
				gt: rangeMin,
				lte: rangeMax,
				label: getShortNumber(rangeMax, 1)
			})

	}

	return pieces.reverse()

}

export function getMapChartOptions(config: MapChartConfig, result: QueryResult) {
	const columns = result.columns
	const rows = result.rows

	const measureColumn = columns.find((c) => FIELDTYPES.MEASURE.includes(c.type))
	const locationColumn = columns.find((c) => FIELDTYPES.DIMENSION.includes(c.type))

	if (!measureColumn || !locationColumn) {
		return null
	}

	let jsonUrl = ''
		if (config.map_type === 'world') {
			jsonUrl = 'world'
		} else if (config.map_type === 'india') {
			jsonUrl = 'india'
	}

	const data = getMapChartData(columns, rows, config)
	const values = data.map((d) => d[1])

	const options: any = {
		height: '100%',
		animation: true,
		animationDuration: 300,
		tooltip: {
			trigger: 'item',
			formatter: (params: any) => {
				// eg. Maharashtra: 1,23,456
				const value = params.value ? getShortNumber(params.value, 2) : '0'
				return `<div class="flex items-center justify-between gap-5">
					<div>${params.name}</div>
					<div class="font-bold">${value}</div>
				</div>`
			}
		},
		visualMap: {
			type: 'piecewise',
			pieces: mapPieces(values),
			itemSymbol: 'circle',
			inRange: {
				color: ['#dbeeff','#b7ddff', '#92cdff','#6ebcff','#4aabff']
			},
		},
		series: [{
			name: measureColumn.name,
			type: 'map',
			map: jsonUrl,
			projection: {
					project: (point: [number, number]) => [point[0] / 180 * Math.PI, -Math.log(Math.tan((Math.PI / 2 + point[1] / 180 * Math.PI) / 2))],
					unproject: (point: [number, number]) => [point[0] * 180 / Math.PI, 2 * 180 / Math.PI * Math.atan(Math.exp(point[1])) - 90]
			},
			data: data.map((d) => ({
				name: d[0],
				value: d[1]
			})),
			itemStyle: {
				color: 'rgb(68, 68, 68)',
				areaColor: 'rgb(243, 243, 243)',
				borderWidth: 0.5,
				borderColor: 'rgb(124, 124, 124)',
			},
			emphasis: false,
			selectedMode: false,
		}],
	}

	return options
}

export function getBubbleChartOptions(config: BubbleChartConfig, result: QueryResult) {
	const _rows = result.rows

	const xColumnName = config.xAxis?.measure_name
	const yColumnName = config.yAxis?.measure_name

	if (!xColumnName || !yColumnName) {
		return null
	}

	const colors = getColors()
	const sizeColumnName = config.size_column?.measure_name
	const nameColumnName = config.dimension?.dimension_name || config.dimension?.column_name
	const groupByColumnName = config.quadrant_column?.dimension_name || config.quadrant_column?.column_name
	const show_data_labels = config.show_data_labels || false

	const scatterData = _rows.map((row) => {
		const xValue = row[xColumnName]
		const yValue = row[yColumnName]
		const sizeValue = sizeColumnName ? row[sizeColumnName] : undefined
		const nameValue = nameColumnName ? row[nameColumnName] : undefined
		const groupValue = groupByColumnName ? row[groupByColumnName] : undefined
		return [xValue, yValue, sizeValue, nameValue, groupValue]
	})

	const seriesMap = new Map<string, any[]>()
	scatterData.forEach((dataPoint) => {
		const groupValue = dataPoint[4]
		if (!seriesMap.has(groupValue)) {
			seriesMap.set(groupValue, [])
		}
		seriesMap.get(groupValue)!.push(dataPoint)
	})

	// calculate symbol size
	let symbolSizeConfig: any = 10
	if (sizeColumnName) {
		const allSizes = _rows.map((r) => r[sizeColumnName]).filter((val) => val != null && !isNaN(val))
		if (allSizes.length > 0) {
			const minSize = Math.min(...allSizes)
			const maxSize = Math.max(...allSizes)
			const sizeRange = maxSize - minSize

			symbolSizeConfig = (value: any[]) => {
				const size = value[2]
				if (size === undefined || size === null || isNaN(size)) return 10
				if (sizeRange === 0) return 20
				const normalized = (size - minSize) / sizeRange
				return 10 + normalized * 25
			}
		}
	}

	const show_legend = !!groupByColumnName && seriesMap.size > 1
	const series = Array.from(seriesMap.entries()).map(([groupName, data], idx) => {
		const color = colors[idx % colors.length]

		const seriesConfig: any = {
			name: groupName,
			type: 'scatter',
			data: data,
			symbolSize: symbolSizeConfig,
			itemStyle: {
				color: color,
			},
			label: {
				show: show_data_labels,
				position: 'top',
				fontSize: 11,
				formatter: (params: any) => {
					if (nameColumnName && params.data[3]) {
						return params.data[3]
					}
					const yVal = params.data[1]
					return isNaN(yVal) ? yVal : getShortNumber(yVal, 1)
				},
			},
			labelLayout: { hideOverlap: true },
			emphasis: {
				itemStyle: {
					borderWidth: 6,
					borderCap: 'round',
					borderJoin: 'round',
				},
			},
		}

		if (idx === 0 && config.show_quadrants) {
			const markLines: any[] = []
			if (config.xAxis_refLine !== undefined && config.xAxis_refLine !== null) {
				markLines.push({
					xAxis: config.xAxis_refLine,
					lineStyle: { type: 'dashed', width: 1.5 },
				})
			}
			if (config.yAxis_refLine !== undefined && config.yAxis_refLine !== null) {
				markLines.push({
					yAxis: config.yAxis_refLine,
					lineStyle: { type: 'dashed', width: 1.5 },
				})
			}
			if (markLines.length > 0) {
				seriesConfig.markLine = {
					silent: true,
					symbol: 'none',
					data: markLines,
				}
			}
		}

		return seriesConfig
	})

	const xColumnLabel = result.columnOptions.find((c) => c.value === xColumnName)?.label || xColumnName
	const yColumnLabel = result.columnOptions.find((c) => c.value === yColumnName)?.label || yColumnName

	const xAxis = {
		...getYAxis(),
		name: xColumnLabel,
		nameLocation: 'middle',
		nameGap: 25,
	}

	const yAxis = {
		...getYAxis(),
		name: yColumnLabel,
		nameLocation: 'middle',
		nameGap: 35,
	}

	const titles: any[] = []

	return {
		animation: true,
		animationDuration: 700,
		color: colors,
		title: titles,
		grid: getGrid({ show_legend }),
		xAxis,
		yAxis,
		series,
		tooltip: {
			trigger: 'item',
			confine: true,
			appendToBody: false,
			formatter: (params: any) => {
				const xVal = params.value[0]
				const yVal = params.value[1]
				const sizeVal = params.value[2]
				const name = params.value[3] || params.seriesName
				const formattedX = isNaN(xVal) ? xVal : formatNumber(xVal)
				const formattedY = isNaN(yVal) ? yVal : formatNumber(yVal)

				let html = `
					<div class="flex flex-col gap-1">
						<div class="font-bold">${name}</div>
						<div class="flex items-center justify-between gap-5">
							<div>${xColumnLabel}:</div>
							<div class="font-bold">${formattedX}</div>
						</div>
						<div class="flex items-center justify-between gap-5">
							<div>${yColumnLabel}:</div>
							<div class="font-bold">${formattedY}</div>
						</div>`

				if (sizeVal !== undefined && sizeVal !== null) {
					const formattedSize = isNaN(sizeVal) ? sizeVal : formatNumber(sizeVal)
					html += `
						<div class="flex items-center justify-between gap-5">
							<div>${sizeColumnName}:</div>
							<div class="font-bold">${formattedSize}</div>
						</div>`
				}

				html += `</div>`
				return html
			},
		},
		legend: getLegend(show_legend),
	}
}

function getGrid(options: any = {}) {
	let bottom = options.show_legend ? 45 : 22;
	if (options.show_scrollbar && !options.swapAxes) {
		bottom += 30;
	}

	return {
		top: 18,
		left: 30,
		right: 30,
		bottom: bottom,
		containLabel: true,
	}
}

function getTooltip(options: any = {}) {
	return {
		trigger: 'axis',
		confine: true,
		appendToBody: false,
		formatter: (params: Object | Array<Object>) => {
			if (Array.isArray(params)) {
				params = params
					.filter((p) => p.value?.[1] !== 0)
					.sort((a, b) => b.value?.[1] - a.value?.[1])
			}

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

function getLegend(show_legend = true, show_scrollbar = false, swap_axes = false) {
	let bottom: string | number = 'bottom';
	if (show_scrollbar && !swap_axes) {
		bottom = 32;
	}

	return {
		show: show_legend,
		icon: 'circle',
		type: 'scroll',
		orient: 'horizontal',
		bottom,
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

export function handleOldXAxisConfig(old_x_axis: any): AxisChartConfig['x_axis'] {
	if (old_x_axis && old_x_axis.column_name) {
		return {
			dimension: old_x_axis,
		}
	}
	return old_x_axis
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

	if (config.x_axis?.dimension) {
		config.x_axis.dimension = setDimensionName(config.x_axis.dimension)
	}
	if (config.split_by?.dimension) {
		config.split_by.dimension = setDimensionName(config.split_by.dimension)
	}
	if (config.date_column) {
		config.date_column = setDimensionName(config.date_column)
	}
	if (config.label_column) {
		config.label_column = setDimensionName(config.label_column)
	}
	if (config.rows && config.rows.length) {
		config.rows = config.rows.map(setDimensionName)
	}
	if (config.columns && config.columns.length) {
		config.columns = config.columns.map(setDimensionName)
	}
	return config
}

export function getGranularity(dimension_name: string, config: ChartConfig) {
	if ('x_axis' in config && config.x_axis.dimension.dimension_name === dimension_name) {
		return config.x_axis.dimension.granularity
	}

	if ('split_by' in config && config.split_by?.dimension?.dimension_name === dimension_name) {
		return config.split_by.dimension.granularity
	}

	if ('date_column' in config && config.date_column?.dimension_name === dimension_name) {
		return config.date_column.granularity
	}

	if ('label_column' in config && config.label_column?.dimension_name === dimension_name) {
		return config.label_column.granularity
	}

	if ('rows' in config) {
		const row = config.rows.find((r: any) => r.dimension_name === dimension_name)
		if (row) return row.granularity
	}

	if ('columns' in config) {
		const column = config.columns.find((c: any) => c.dimension_name === dimension_name)
		if (column) return column.granularity
	}
}
