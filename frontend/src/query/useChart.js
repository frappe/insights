import { useQuery } from '@/query/useQueries'
import { safeJSONParse } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { guessChart } from '@/widgets/useChartData'
import { watchDebounced, watchOnce } from '@vueuse/core'
import { call, createDocumentResource, debounce } from 'frappe-ui'
import { reactive } from 'vue'

const charts = {}

export async function createChart() {
	return call('insights.api.create_chart')
}

export default function useChart(name) {
	if (!charts[name]) {
		charts[name] = getChart(name)
	}
	return charts[name]
}

function getChart(chartName) {
	const chartDocResource = getChartResource(chartName)
	const state = reactive({
		query: null,
		data: [],
		columns: [],
		loading: false,
		error: null,
		options: {},
		autosave: false,
		doc: {
			doctype: 'Insights Chart',
			name: undefined,
			chart_type: undefined,
			options: {},
			is_public: false,
		},
	})

	async function load() {
		state.loading = true
		await chartDocResource.get.fetch()
		state.doc = chartDocResource.doc
		if (!state.doc.query) {
			state.loading = false
			return
		}
		state.doc.query = chartDocResource.doc.query
		updateChartData()
	}
	load()

	function updateChartData() {
		state.loading = true
		const _query = useQuery(state.doc.query)
		watchOnce(
			() => _query.doc,
			() => {
				if (!_query.doc) return
				state.data = getFormattedResult(_query.doc.results)
				state.columns = state.data[0]
				if (!state.doc.chart_type) {
					const recommendedChart = guessChart(state.data)
					state.doc.chart_type = recommendedChart?.type
					state.doc.options = recommendedChart?.options
				}
				state.doc.options.query = state.doc.query
				state.loading = false
			}
		)
	}

	function save() {
		chartDocResource.setValue.submit({
			chart_type: state.doc.chart_type,
			options: state.doc.options,
		})
	}

	function togglePublicAccess(isPublic) {
		if (state.doc.is_public === isPublic) return
		chartDocResource.setValue.submit({ is_public: isPublic }).then(() => {
			$notify({
				title: 'Chart access updated',
				appearance: 'success',
			})
			state.doc.is_public = isPublic
		})
	}

	function updateQuery(query) {
		if (!query) return
		if (state.doc.query === query) return
		state.doc.query = query
		chartDocResource.setValue.submit({ query }).then(() => {
			updateChartData()
		})
	}
	updateQuery = debounce(updateQuery, 500)

	let autosaveWatcher = undefined
	function enableAutoSave() {
		state.autosave = true
		autosaveWatcher = watchDebounced(() => state.doc, save, {
			deep: true,
			debounce: 500,
		})
	}
	function disableAutoSave() {
		state.autosave = false
		if (autosaveWatcher) {
			autosaveWatcher()
			autosaveWatcher = undefined
		}
	}

	return Object.assign(state, {
		load,
		save,
		togglePublicAccess,
		updateQuery,
		enableAutoSave,
		disableAutoSave,
		delete: chartDocResource.delete.submit,
	})
}

function getChartResource(chartName) {
	return createDocumentResource({
		doctype: 'Insights Chart',
		name: chartName,
		transform: (doc) => {
			doc.chart_type = doc.chart_type
			doc.options = safeJSONParse(doc.options)
			doc.options.query = doc.query
			return doc
		},
	})
}
