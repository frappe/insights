import { getChartResource } from '@/query/useChart'
import { areDeeplyEqual, createTaskRunner } from '@/utils'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import { computed, ref, watch } from 'vue'

export default async function useChart(query) {
	const chartName = await query.getChartName()
	const chartResource = getChartResource(chartName)
	await chartResource.get.fetch()

	const chartData = ref([])

	const run = createTaskRunner()
	watch(
		() => ({
			title: chartResource.doc.title,
			chart_type: chartResource.doc.chart_type,
			options: chartResource.doc.options,
		}),
		updateDoc,
		{ deep: true }
	)
	async function updateDoc(doc) {
		if (!doc.chart_type) return
		const oldValues = {
			title: chartResource.originalDoc.title,
			chart_type: chartResource.originalDoc.chart_type,
			options: chartResource.originalDoc.options,
		}
		const newValues = {
			title: doc.title,
			chart_type: doc.chart_type,
			options: doc.options,
		}
		if (areDeeplyEqual(newValues, oldValues)) return
		await run(() => chartResource.setValue.submit(newValues))
	}

	watch(
		() => query.formattedResults,
		() => {
			if (!query.formattedResults.length) {
				chartResource.doc.chart_type = null
				chartResource.doc.options = {}
				updateDoc(chartResource.doc)
				return
			}
			chartData.value = convertResultToObjects(query.formattedResults)
			const recommendedChart = guessChart(query.formattedResults)
			chartResource.doc.chart_type = recommendedChart?.type
			chartResource.doc.options.title = query.doc.title
			chartResource.doc.options.query = query.doc.name
			chartResource.doc.options = {
				...chartResource.doc.options,
				...recommendedChart?.options,
			}
			updateDoc(chartResource.doc)
		},
		{ immediate: true, deep: true }
	)

	function togglePublicAccess(isPublic) {
		if (chartResource.doc.is_public === isPublic) return
		chartResource.setValue.submit({ is_public: isPublic }).then(() => {
			$notify({
				title: 'Chart access updated',
				variant: 'success',
			})
			chartResource.doc.is_public = isPublic
		})
	}

	async function addToDashboard(dashboardName) {
		if (!dashboardName || !chartResource.doc.name || chartResource.addingToDashboard) return
		chartResource.addingToDashboard = true
		await call('insights.api.dashboards.add_chart_to_dashboard', {
			dashboard: dashboardName,
			chart: chartResource.doc.name,
		})
		chartResource.addingToDashboard = false
	}

	return {
		doc: computed({
			get: () => chartResource.doc,
			set: (value) => (chartResource.doc = value),
		}),
		data: chartData,
		togglePublicAccess,
		addToDashboard,
	}
}
