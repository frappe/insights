import { formatNumber, getShortNumber } from '@/utils'
import { getColors as getDefaultColors } from '@/utils/colors'
import { graphic } from 'echarts/core'

export default function getAxisChartOptions({ chartType, options, data }) {
	const xAxisColumns = getXAxisColumns(options, data)
	const xAxisValues = getXAxisValues(xAxisColumns, data)
	const datasets = makeDatasets(options, data, xAxisColumns, xAxisValues)
	return makeOptions(chartType, xAxisValues, datasets, options)
}

function getXAxisColumns(options, data) {
	if (!options.xAxis || !options.xAxis.length) return []
	const xAxisOptions = handleLegacyAxisOptions(options.xAxis)
	// remove the columns that might be removed from the query but not the chart
	return xAxisOptions
		.filter((xAxisOption) => data[0]?.hasOwnProperty(xAxisOption.column))
		.map((op) => op.column)
}

function getXAxisValues(xAxisColumns, data) {
	if (!data?.length) return []
	if (!xAxisColumns.length) return []

	let firsXAxisColumn = xAxisColumns[0]
	if (typeof firsXAxisColumn !== 'string') {
		return console.warn('Invalid X-Axis option. Please re-select the X-Axis option.')
	}

	const values = data.map((d) => d[firsXAxisColumn])
	return [...new Set(values)]
}

function makeDatasets(options, data, xAxisColumns, xAxisValues) {
	let yAxis = options.yAxis
	if (!data?.length || !yAxis?.length) return []
	yAxis = handleLegacyAxisOptions(yAxis)

	const validYAxisOptions = yAxis
		// to exclude the columns that might be removed from the query but not the chart
		.filter(
			(yAxisOption) =>
				data[0].hasOwnProperty(yAxisOption?.column) || data[0].hasOwnProperty(yAxisOption)
		)

	if (xAxisColumns.length == 1) {
		// even if data has multiple points for each xAxisColumn
		// for eg. Oct has 3 price for each category
		// Month  Category  Price
		// Oct    A         10
		// Oct    B         20
		// Oct    C         30
		// so, we need to sum up the prices of each unique month
		const xAxisColumn = xAxisColumns[0]
		return validYAxisOptions.map((option) => {
			const column = option.column || option
			const seriesOptions = option.series_options || {}
			const _data = xAxisValues.map((xAxisValue) => {
				const points = data.filter((d) => d[xAxisColumn] === xAxisValue)
				const sum = points.reduce((acc, curr) => acc + curr[column], 0)
				return sum
			})
			return {
				label: column,
				data: _data,
				series_options: seriesOptions,
			}
		})
	}

	// if multiple xAxis columns are selected
	// then consider first xAxis column as labels
	// and other xAxis columns' values as series
	const datasets = []
	const firstAxisColumn = xAxisColumns[0]
	const restAxisColumns = xAxisColumns.slice(1)

	for (let yAxisOption of validYAxisOptions) {
		const datamap = {}
		const column = yAxisOption.column || yAxisOption // "count"
		const seriesOptions = yAxisOption.series_options || {} // { type: "bar" }

		for (let xAxisOption of restAxisColumns) {
			// ["fruit"]
			let subXAxisValues = [...new Set(data.map((d) => d[xAxisOption]))] // fruit = ["apple", "banana"]
			for (let subXAxisValue of subXAxisValues) {
				// "Apple"
				let subXAxisData = data.filter((d) => d[xAxisOption] === subXAxisValue) // row with Apple
				for (let xAxisValue of xAxisValues) {
					// ["Monday", "Tuesday"]
					let dataSetStack = subXAxisData.find(
						(row) => row[firstAxisColumn] == xAxisValue
					) // row with Apple and Monday

					// check if datamap has key subXAxisValue
					// add subXAxisValue: [dataSetStack.column]
					// if not dataSetStack.column, append 0 to datamap[subXAxisValue]
					let value = dataSetStack?.[column] || 0
					if (subXAxisValue in datamap) {
						datamap[subXAxisValue].push(value)
					} else {
						datamap[subXAxisValue] = [value]
					}
				}
			}
		}
		for (const [label, data] of Object.entries(datamap)) {
			datasets.push({
				label,
				data,
				series_options: seriesOptions,
			})
		}
	}

	return datasets
}

function makeOptions(chartType, labels, datasets, options) {
	if (!datasets?.length) return {}

	const colors = options.colors?.length
		? [...options.colors, ...getDefaultColors()]
		: getDefaultColors()

	return {
		animation: false,
		color: colors,
		grid: {
			top: 15,
			bottom: 35,
			left: 25,
			right: 35,
			containLabel: true,
		},
		xAxis: {
			axisType: 'xAxis',
			type: 'category',
			axisTick: false,
			data: labels,
			splitLine: {
				show: chartType == 'scatter',
				lineStyle: { type: 'dashed' },
			},
			axisLabel: {
				rotate: options.rotateLabels,
				formatter: (value, _) => (!isNaN(value) ? getShortNumber(value, 1) : value),
			},
		},
		yAxis: datasets.map((dataset) => ({
			name: options.splitYAxis ? dataset.label : undefined,
			nameGap: 45,
			nameLocation: 'middle',
			nameTextStyle: { color: 'transparent' },
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed' },
			},
			axisLabel: {
				formatter: (value, _) => (!isNaN(value) ? getShortNumber(value, 1) : value),
			},
			min: options.yAxisMin,
			max: options.yAxisMax,
		})),
		series: datasets.map((dataset, index) => ({
			name: dataset.label,
			data: dataset.data,
			type: chartType || dataset.series_options.type || 'bar',
			yAxisIndex: options.splitYAxis ? index : 0,
			color: dataset.series_options.color || colors[index],
			markLine: getMarkLineOption(options),
			// line styles
			smoothMonotone: 'x',
			smooth: dataset.series_options.smoothLines || options.smoothLines ? 0.4 : false,
			showSymbol: dataset.series_options.showPoints || options.showPoints,
			symbolSize: chartType == 'scatter' ? 10 : 5,
			areaStyle:
				dataset.series_options.showArea || options.showArea
					? {
							color: new graphic.LinearGradient(0, 0, 0, 1, [
								{ offset: 0, color: dataset.series_options.color || colors[index] },
								{ offset: 1, color: '#fff' },
							]),
							opacity: 0.2,
					  }
					: undefined,
			// bar styles
			itemStyle: {
				borderRadius:
					options.roundedBars != undefined && index == datasets.length - 1
						? [4, 4, 0, 0]
						: 0,
			},
			barMaxWidth: 50,
			stack: options.stack ? 'stack' : null,
		})),
		legend: {
			icon: 'circle',
			type: 'scroll',
			bottom: 'bottom',
			pageIconSize: 12,
			pageIconColor: '#64748B',
			pageIconInactiveColor: '#C0CCDA',
			pageFormatter: '{current}',
			pageButtonItemGap: 2,
		},
		tooltip: {
			trigger: 'axis',
			confine: true,
			appendToBody: false,
			valueFormatter: (value) => (isNaN(value) ? value : formatNumber(value)),
		},
	}
}

function getMarkLineOption(options) {
	return options.referenceLine
		? {
				data: [
					{
						name: options.referenceLine,
						type: options.referenceLine.toLowerCase(),
						label: { position: 'middle', formatter: '{b}: {c}' },
					},
				],
		  }
		: {}
}

function handleLegacyAxisOptions(axisOptions) {
	// if axisOptions = 'column1'
	if (typeof axisOptions === 'string') {
		axisOptions = [{ column: axisOptions }]
	}
	// if axisOptions = ['column1', 'column2']
	if (Array.isArray(axisOptions) && typeof axisOptions[0] === 'string') {
		axisOptions = axisOptions.map((column) => ({ column }))
	}
	return axisOptions
}
