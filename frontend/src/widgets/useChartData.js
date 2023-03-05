import { useQuery } from '@/query/useQueries'
import { getFormattedResult } from '@/utils/query/results'
import { watchOnce } from '@vueuse/core'
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
		loading: false,
		error: null,
	})

	function load(query) {
		if (!query) return

		let rawResults = []
		state.loading = true
		const _query = useQuery(query)
		watchOnce(
			() => _query.doc,
			async () => {
				if (!_query.doc) return
				rawResults = options.resultsFetcher
					? await options.resultsFetcher()
					: _query.doc.results
				state.loading = false
				state.data = getFormattedResult(rawResults || [], _query.doc.columns || [])
			}
		)
	}

	if (options.query) {
		load(options.query)
	}

	return Object.assign(state, {
		load,
	})
}
