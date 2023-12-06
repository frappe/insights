import { areDeeplyEqual, createTaskRunner, safeJSONParse } from '@/utils'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import { watchDebounced } from '@vueuse/core'
import { call, createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'
import useQuery from './useQuery'

export default async function useChart(chart_name) {
	const resource = getChartResource(chart_name)
	await resource.get.fetch()

	const chart = reactive({
		doc: resource.doc,
		data: [],
		togglePublicAccess,
		addToDashboard,
		getGuessedChart,
		resetOptions,
		delete: deleteChart,
	})

	const query = useQuery(chart.doc.query)
	chart.data = computed(() => convertResultToObjects(query.formattedResults))
	chart.doc.options.title = chart.doc.options?.title || query.doc?.title

	const run = createTaskRunner()
	watchDebounced(
		() => ({
			title: chart.doc.title,
			chart_type: chart.doc.chart_type,
			options: chart.doc.options,
		}),
		_updateDoc,
		{ deep: true, debounce: 1000 }
	)
	async function _updateDoc(newDoc) {
		newDoc.options.query = query.doc.name
		if (newDoc.chart_type == 'Auto') {
			newDoc.options = { title: newDoc.title }
		}

		const ogDoc = resource.originalDoc
		const chartTypeChanged = newDoc.chart_type != ogDoc.chart_type
		if (
			!chartTypeChanged &&
			newDoc.title == ogDoc.title &&
			newDoc.options.query == ogDoc.options.query &&
			areDeeplyEqual(newDoc.options, ogDoc.options)
		)
			return

		if (chartTypeChanged && newDoc.chart_type != 'Auto') {
			const guessedChart = getGuessedChart(newDoc.chart_type)
			newDoc.options = { ...guessedChart.options, ...newDoc.options }
		}

		_save(newDoc)
	}

	function _save(chart) {
		return run(() =>
			resource.setValue
				.submit({
					title: chart.title,
					chart_type: chart.chart_type,
					options: chart.options,
				})
				.then(() => (chart.doc = resource.doc))
		)
	}

	function getGuessedChart(chart_type) {
		const recommendedChart = guessChart(query.formattedResults, chart_type)
		return {
			chart_type: recommendedChart?.type,
			options: {
				...recommendedChart?.options,
			},
		}
	}

	function togglePublicAccess(isPublic) {
		if (resource.doc.is_public === isPublic) return
		resource.setValue.submit({ is_public: isPublic }).then(() => {
			$notify({
				title: 'Chart access updated',
				variant: 'success',
			})
			resource.doc.is_public = isPublic
		})
	}

	async function addToDashboard(dashboardName) {
		if (!dashboardName || !resource.doc.name || resource.addingToDashboard) return
		resource.addingToDashboard = true
		await call('insights.api.dashboards.add_chart_to_dashboard', {
			dashboard: dashboardName,
			chart: resource.doc.name,
		})
		resource.addingToDashboard = false
	}

	function resetOptions() {
		state.doc.chart_type = undefined
		state.doc.options = {}
	}

	async function deleteChart() {
		state.deleting = true
		return run(() => resource.delete.submit().then(() => (state.deleting = false)))
	}

	return chart
}

export function getChartResource(chartName) {
	return createDocumentResource({
		doctype: 'Insights Chart',
		name: chartName,
		auto: false,
		transform: (doc) => {
			doc.chart_type = doc.chart_type
			doc.options = safeJSONParse(doc.options)
			return doc
		},
	})
}
