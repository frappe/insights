import { getChartResource } from '@/query/useChart'
import { areDeeplyEqual, createTaskRunner } from '@/utils'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import { useStorage, watchDebounced } from '@vueuse/core'
import { computed, reactive } from 'vue'

export default async function useChart(query) {
	const chartName = await getChartName(query)
	const resource = getChartResource(chartName)
	await resource.get.fetch()

	const chart = reactive({
		doc: resource.doc,
		data: computed(() => convertResultToObjects(query.formattedResults)),
		togglePublicAccess,
		addToDashboard,
		getGuessedChart,
	})

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
		if (newDoc.chart_type == 'Auto')
			newDoc.options = {
				title: newDoc.title,
				query: query.doc.name,
			}

		const ogDoc = resource.originalDoc
		if (
			newDoc.title == ogDoc.title &&
			newDoc.chart_type == ogDoc.chart_type &&
			areDeeplyEqual(newDoc.options, ogDoc.options)
		)
			return

		_save(newDoc)
	}

	function _save(chart) {
		return run(() =>
			resource.setValue.submit({
				title: chart.title,
				chart_type: chart.chart_type,
				options: chart.options,
			})
		)
	}

	function getGuessedChart() {
		const recommendedChart = guessChart(query.formattedResults)
		return {
			chart_type: recommendedChart?.type,
			options: {
				title: query.doc.title,
				query: query.doc.name,
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

	return chart
}

const chartNameCache = useStorage('insights:chart_name_cache', {})
function getChartName(query) {
	if (chartNameCache[query.doc.name]) return chartNameCache[query.doc.name]
	return query.getChartName().then((name) => {
		chartNameCache[query.doc.name] = name
		return name
	})
}
