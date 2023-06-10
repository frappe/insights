import { useQuery } from '@/query/useQueries'
import { safeJSONParse } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { guessChart } from '@/widgets/useChartData'
import { watchDebounced, watchOnce } from '@vueuse/core'
import { createDocumentResource } from 'frappe-ui'
import { reactive, watch } from 'vue'

const charts = {}

export default function useChart(name) {
	if (!charts[name]) {
		charts[name] = makeChart(name)
	}
	return charts[name]
}

function makeChart(chartName) {
	const chartDocResource = getChartResource(chartName)
	const state = reactive({
		query: null,
		data: [],
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
		state.doc.query = chartDocResource.doc.query
		const _query = useQuery(state.doc.query)
		watchOnce(
			() => _query.doc,
			() => {
				if (!_query.doc) return
				state.data = getFormattedResult(_query.doc.results)
				if (!state.doc.chart_type) {
					const recommendedChart = guessChart(state.data)
					state.doc.chart_type = recommendedChart?.type
					state.doc.options = recommendedChart?.options
					state.doc.options.title = _query.doc.title
				}
				state.doc.options.query = state.doc.query
				state.loading = false
				state.doc.options.query = state.doc.query
			}
		)
	}
	load()

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

	let autosaveWatcher = undefined
	watch(
		() => state.autosave,
		(val) => {
			if (val) {
				autosaveWatcher = watchDebounced(() => state.doc, save, {
					deep: true,
					debounce: 500,
				})
			}
			if (!val && autosaveWatcher) {
				autosaveWatcher()
				autosaveWatcher = undefined
			}
		}
	)

	return Object.assign(state, {
		load,
		save,
		togglePublicAccess,
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
