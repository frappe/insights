import { FIELDTYPES } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { reactive } from 'vue'

/**
 * @param {Object} options
 * @param {Object} options.query
 * @param {Object} options.resultsFetcher
 * @returns {Object} chartData
 * @returns {Array} chartData.data
 * @returns {Boolean} chartData.loading
 * @returns {Boolean} chartData.error
 * @returns {Function} chartData.reload
 *
 * @example
 * const chartData = useChartData(options)
 * chartData.load(query)
 **/

export default function useChartData(options = {}) {
	const state = reactive({
		query: null,
		data: [],
		rawData: [],
		recommendedChart: {},
		loading: false,
		error: null,
	})

	function load(query) {
		if (!query) return
		state.loading = true
		return options
			.resultsFetcher()
			.then((results) => {
				state.loading = false
				state.rawData = getFormattedResult(results)
				state.data = convertResultToObjects(state.rawData)
			})
			.catch((error) => {
				state.loading = false
				state.error = error
			})
	}

	if (options.query) {
		load(options.query)
	}

	function getGuessedChart(chart_type) {
		return guessChart(state.rawData, chart_type)
	}

	return Object.assign(state, {
		load,
		getGuessedChart,
	})
}

export function guessChart(dataset, chart_type) {
	const [columns, ...rows] = dataset
	const numberColumns = columns.filter((col) => FIELDTYPES.NUMBER.includes(col.type))
	const dateColumns = columns.filter((col) => FIELDTYPES.DATE.includes(col.type))
	const stringColumns = columns.filter((col) => FIELDTYPES.TEXT.includes(col.type))

	// if there is only one number column, it's a number chart
	const hasOnlyOneNumberColumn = columns.length === 1 && numberColumns.length === 1
	const autoGuessNumberChart = chart_type === 'Auto' && hasOnlyOneNumberColumn
	const shouldGuessNumberChart = chart_type === 'Number' && numberColumns.length >= 1
	if (autoGuessNumberChart || shouldGuessNumberChart) {
		return {
			type: 'Number',
			options: {
				column: numberColumns[0].label,
				shorten: false,
			},
		}
	}

	// if there is at least one date column and one number column, it's a line chart
	const hasAtLeastOneDateAndNumberColumn = dateColumns.length >= 1 && numberColumns.length >= 1
	const autoGuessLineChart = chart_type === 'Auto' && hasAtLeastOneDateAndNumberColumn
	const shouldGuessLineChart = chart_type === 'Line' && hasAtLeastOneDateAndNumberColumn
	if (autoGuessLineChart || shouldGuessLineChart) {
		let splitYAxis = false
		if (numberColumns.length === 2) {
			try {
				const numberColumnIndexes = numberColumns.map((col) =>
					columns.findIndex((c) => c === col)
				)
				const maxValue1 = Math.max(...rows.map((row) => row[numberColumnIndexes[0]]))
				const maxValue2 = Math.max(...rows.map((row) => row[numberColumnIndexes[1]]))
				// if maxValue1 is 10 times bigger than maxValue2, then split the y-axis
				const biggerMaxValue = Math.max(maxValue1, maxValue2)
				const smallerMaxValue = Math.min(maxValue1, maxValue2)
				splitYAxis = Boolean(biggerMaxValue / smallerMaxValue > 10)
			} catch (e) {
				console.log(e)
			}
		}
		return {
			type: 'Line',
			options: {
				xAxis: [{ column: dateColumns[0].label }],
				yAxis: numberColumns.map((col) => ({ column: col.label })),
				splitYAxis: splitYAxis,
			},
		}
	}

	const hasAtLeastOneStringAndNumberColumn =
		stringColumns.length >= 1 && numberColumns.length >= 1
	const stringColIndex = columns.findIndex((col) => FIELDTYPES.TEXT.includes(col.type))
	const uniqueValuesCount = new Set(rows.map((row) => row[stringColIndex])).size
	// if there is only one string column and one number column,
	// and there are less than 10 unique values, it's a pie chart
	const hasLessThan10UniqueValues = uniqueValuesCount <= 10
	const hasOnlyOneStringAndNumberColumn = stringColumns.length === 1 && numberColumns.length === 1
	const autoGuessPieChart =
		chart_type === 'Auto' && hasOnlyOneStringAndNumberColumn && hasLessThan10UniqueValues
	const shouldGuessPieChart = chart_type === 'Pie'
	if (autoGuessPieChart || shouldGuessPieChart) {
		return {
			type: 'Pie',
			options: {
				xAxis: stringColumns[0]?.label,
				yAxis: numberColumns[0]?.label,
			},
		}
	}

	// if there is at least one string column and one number column, it's a bar chart
	const hasAtLeastOneDateOrStringColumn = dateColumns.length >= 1 || stringColumns.length >= 1
	const autoGuessBarChart = chart_type === 'Auto' && hasAtLeastOneDateOrStringColumn
	const shouldGuessBarChart = chart_type === 'Bar'
	if (autoGuessBarChart || shouldGuessBarChart) {
		const xAxis = stringColumns.length
			? stringColumns[0].label
			: dateColumns.length
			? dateColumns[0].label
			: ''
		const uniqueXValuesCount = new Set(rows.map((row) => row[xAxis])).size
		return {
			type: 'Bar',
			options: {
				xAxis: xAxis,
				yAxis: numberColumns.map((col) => col.label),
				rotateLabels: uniqueXValuesCount > 10 ? '90' : '0',
			},
		}
	}

	const shouldGuessPivotChart = chart_type === 'Pivot Table'
	if (shouldGuessPivotChart) {
		return {
			type: 'Pivot Table',
			options: {
				rows: [...dateColumns, ...stringColumns].map((col) => ({
					label: col.label,
					value: col.label,
				})),
				values: [...numberColumns].map((col) => ({ label: col.label, value: col.label })),
			},
		}
	}

	const autoGuessTableChart = chart_type === 'Auto'
	const shouldGuessTableChart = chart_type === 'Table'
	if (autoGuessTableChart || shouldGuessTableChart) {
		return {
			type: 'Table',
			options: { columns: columns.map((col) => col.label) },
		}
	}

	return { type: chart_type, options: {} }
}

export function convertResultToObjects(results) {
	if (!results?.length) return []
	// results first row is an list of dicts with label and type
	// return list of plain objects with first row's labels as keys
	// return [{ label1: value1, label2: value2 }, ...}]
	return results.slice(1).map((row) => {
		return results[0].reduce((obj, { label }, index) => {
			obj[label] = row[index]
			return obj
		}, {})
	})
}
