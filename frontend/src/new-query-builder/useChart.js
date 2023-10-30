import { getChartResource } from '@/query/useChart'
import { getFormattedResult } from '@/utils/query/results'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import { computed, ref, watch } from 'vue'

export default async function useChart(query) {
	const chartName = await query.getChartName()
	const chartResource = getChartResource(chartName)
	await chartResource.get.fetch()

	const chartDoc = computed({
		get: () => chartResource.doc,
		set: (value) => (chartResource.doc = value),
	})
	const chartData = ref(null)

	watch(
		() => query.doc.results,
		() => {
			const formattedResults = getFormattedResult(query.doc.results)
			chartData.value = convertResultToObjects(formattedResults)

			if (!formattedResults.length) {
				chartResource.doc.chart_type = null
				chartResource.doc.options = {}
				return
			}

			const recommendedChart = guessChart(formattedResults)
			chartResource.doc.chart_type = recommendedChart?.type
			chartResource.doc.options = recommendedChart?.options
			chartResource.doc.options.title = query.doc.title
			chartResource.doc.options.query = query.doc.name
		},
		{ immediate: true, deep: true }
	)

	return {
		chartDoc,
		chartData,
	}
}
