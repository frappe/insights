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
		recommendedChart: {},
		loading: false,
		error: null,
	})

	function load(query) {
		if (!query) return
		state.loading = true
		options.resultsFetcher().then((results) => {
			state.loading = false
			const formattedResults = getFormattedResult(results)
			state.data = convertResultToObjects(formattedResults)
			state.recommendedChart = guessChart(formattedResults)
		})
	}

	if (options.query) {
		load(options.query)
	}

	return Object.assign(state, {
		load,
	})
}

export function guessChart(dataset) {
	const [columns, ...rows] = dataset
	const numberColumns = columns.filter((col) => FIELDTYPES.NUMBER.includes(col.type))
	const dateColumns = columns.filter((col) => FIELDTYPES.DATE.includes(col.type))
	const stringColumns = columns.filter((col) => FIELDTYPES.TEXT.includes(col.type))

	// if there is only one number column, it's a number chart
	if (columns.length === 1 && numberColumns.length === 1) {
		return {
			type: 'Number',
			options: {
				column: numberColumns[0].label,
			},
		}
	}

	// if there is only one string column and one number column, it's a pie chart
	if (stringColumns.length === 1 && numberColumns.length === 1) {
		return {
			type: 'Pie',
			options: {
				xAxis: stringColumns[0].label,
				yAxis: numberColumns[0].label,
			},
		}
	}

	// if there is at least one date column and one number column, it's a line chart
	if (dateColumns.length >= 1 && numberColumns.length >= 1) {
		return {
			type: 'Line',
			options: {
				xAxis: dateColumns[0].label,
				yAxis: numberColumns.map((col) => col.label),
			},
		}
	}
	// if there is at least one string column and one number column, it's a bar chart
	if (stringColumns.length >= 1 && numberColumns.length >= 1) {
		const uniqueValuesCount = new Set(rows.map((row) => row[stringColumns[0].label])).size
		return {
			type: 'Bar',
			options: {
				xAxis: stringColumns[0].label,
				yAxis: numberColumns.map((col) => col.label),
				rotateLabels: uniqueValuesCount > 10 ? '90' : '0',
			},
		}
	}

	return {
		type: 'Table',
		options: { columns: columns.map((col) => col.label) },
	}
}

export function convertResultToObjects(results) {
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
