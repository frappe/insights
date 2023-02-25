import { useQuery } from '@/query/useQueries'
import { getFormattedResult } from '@/utils/query/results'
import { reactive } from 'vue'
import { watchOnce } from '@vueuse/core'

/**
 * @param {Object} chart
 * @param {String} chart.query
 * @param {Object} chart.resultsFetcher
 * @returns {Object} chartData
 * @returns {Array} chartData.data
 * @returns {Boolean} chartData.loading
 * @returns {Boolean} chartData.error
 * @returns {Function} chartData.reload
 *
 * @example
 * const { data, loading, error, reload } = useChartData(chart)
 **/

export default function useChartData(chart) {
	const state = reactive({
		data: [],
		loading: false,
		error: null,
	})

	function reload() {
		state.loading = true
		state.error = null
		loadChartData()
	}
	reload()

	function loadChartData() {
		let rawResults = []
		const query = useQuery(chart.query)
		watchOnce(
			() => query.doc,
			async () => {
				if (!query.doc) return
				rawResults = chart.resultsFetcher ? await chart.resultsFetcher() : query.doc.results
				state.loading = false
				state.data = getFormattedResult(rawResults || [], query.doc.columns || [])
			}
		)
	}

	return Object.assign(state, {
		reload,
	})
}
