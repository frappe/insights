import { areDeeplyEqual, createTaskRunner, safeJSONParse } from '@/utils'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import { watchDebounced } from '@vueuse/core'
import { call, createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'

export default function useQueryChart(chartName, queryTitle, queryResults) {
	const resource = getChartResource(chartName)
	resource.get.fetch()

	const chart = reactive({
		doc: computed(() => resource.doc || {}),
		data: computed(() => convertResultToObjects(queryResults.formattedResults)),
		togglePublicAccess,
		addToDashboard,
		getGuessedChart,
		resetOptions,
		delete: deleteChart,
	})

	const run = createTaskRunner()
	watchDebounced(
		() => ({
			chart_type: chart.doc.chart_type,
			options: chart.doc.options,
		}),
		_updateDoc,
		{ deep: true, debounce: 1000 }
	)
	async function _updateDoc(newDoc) {
		const ogDoc = resource.originalDoc
		const chartTypeChanged = newDoc.chart_type != ogDoc.chart_type
		const optionsChanged = !areDeeplyEqual(newDoc.options, ogDoc.options)
		if (!chartTypeChanged && !optionsChanged) return

		let newOptions = { ...newDoc.options }
		if (!newOptions.query) {
			newOptions.query = chart.doc.query
		}

		if (chartTypeChanged && newDoc.chart_type != 'Auto') {
			const guessedChart = getGuessedChart(newDoc.chart_type)
			newOptions = { ...guessedChart.options, ...newOptions }
			newOptions.title = queryTitle
		}
		_save({ chart_type: newDoc.chart_type, options: newOptions })
	}

	function _save(chartDoc) {
		chartDoc.options.query = chart.doc.query
		return run(() =>
			resource.setValue.submit({
				title: chartDoc.options.title || queryTitle,
				chart_type: chartDoc.chart_type,
				options: chartDoc.options,
			})
		)
	}

	function getGuessedChart(chart_type) {
		if (!queryResults.formattedResults.length) return
		chart_type = chart_type || chart.doc.chart_type
		const recommendedChart = guessChart(queryResults.formattedResults, chart_type)
		return {
			chart_type: recommendedChart?.type,
			options: {
				...recommendedChart?.options,
				title: recommendedChart?.options?.title || queryTitle,
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
		if (chart.doc.chart_type == 'Auto') {
			const guessedChart = getGuessedChart()
			await _save({
				chart_type: guessedChart.chart_type,
				options: guessedChart.options,
			})
		}
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
