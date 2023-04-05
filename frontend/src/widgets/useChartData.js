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
			state.data = getFormattedResult(results)
			state.recommendedChart = guessChart(state.data)
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
	const [headers, ...rows] = dataset
	const columnNames = headers.map((header) => header.label)
	const columnTypes = headers.map((header) => header.type)
	const numberColIndex = columnTypes.findIndex((type) => FIELDTYPES.NUMBER.includes(type))
	const dateColIndex = columnTypes.findIndex((type) => FIELDTYPES.DATE.includes(type))
	const stringColIndex = columnTypes.findIndex((type) => FIELDTYPES.TEXT.includes(type))

	// if there is only one number column, it's a number chart
	if (columnTypes.length === 1 && numberColIndex !== -1) {
		return {
			type: 'Number',
			options: {
				column: columnNames[numberColIndex],
			},
		}
	}
	// if there is one date column and one number column, it's a line chart
	if (dateColIndex !== -1 && numberColIndex !== -1) {
		return {
			type: 'Line',
			options: {
				xAxis: columnNames[dateColIndex],
				yAxis: [columnNames[numberColIndex]],
			},
		}
	}
	// if there is one string column and one number column, it's a bar chart
	if (stringColIndex !== -1 && numberColIndex !== -1) {
		// if there are less than 10 unique values in the string column, it's a pie chart
		const uniqueValuesCount = new Set(rows.map((row) => row[stringColIndex])).size
		if (uniqueValuesCount <= 8) {
			return {
				type: 'Pie',
				options: {
					xAxis: columnNames[stringColIndex],
					yAxis: columnNames[numberColIndex],
				},
			}
		}
		return {
			type: 'Bar',
			options: {
				xAxis: columnNames[stringColIndex],
				yAxis: [columnNames[numberColIndex]],
				rotateLabels: uniqueValuesCount > 10 ? '90' : '0',
			},
		}
	}

	return {
		type: 'Table',
		options: {
			columns: headers,
		},
	}
}
