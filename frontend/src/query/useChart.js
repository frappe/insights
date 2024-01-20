import { useQueryResource } from '@/query/useQueryResource'
import { safeJSONParse, whenHasValue } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import { watchDebounced, watchOnce } from '@vueuse/core'
import { call, createDocumentResource, debounce } from 'frappe-ui'
import { reactive } from 'vue'
import useQuery from './resources/useQuery'

const charts = {}

export async function createChart() {
	return call('insights.api.queries.create_chart')
}

export default function useChartOld(name) {
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
		_query.reload()
		watchOnce(
			() => _query.results.doc,
			() => {
				if (!_query.doc) return
				state.columns = _query.results.columns
				const formattedResults = _query.results.formattedResults
				state.data = convertResultToObjects(formattedResults)
				if (!state.doc.chart_type) {
					const recommendedChart = guessChart(formattedResults)
					state.doc.chart_type = recommendedChart?.type
					state.doc.options = recommendedChart?.options
					state.doc.options.title = _query.doc.title
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
				variant: 'success',
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

	async function deleteChart() {
		state.deleting = true
		await chartDocResource.delete.submit()
		state.deleting = false
	}

	async function addToDashboard(dashboardName) {
		if (!dashboardName || !state.doc.name || state.addingToDashboard) return
		state.addingToDashboard = true
		await call('insights.api.dashboards.add_chart_to_dashboard', {
			dashboard: dashboardName,
			chart: state.doc.name,
		})
		state.addingToDashboard = false
	}

	function resetOptions() {
		state.doc.chart_type = undefined
		state.doc.options = {}
	}

	return Object.assign(state, {
		load,
		save,
		togglePublicAccess,
		updateQuery,
		enableAutoSave,
		disableAutoSave,
		addToDashboard,
		resetOptions,
		delete: deleteChart,
	})
}

export function getChartResource(chartName) {
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
