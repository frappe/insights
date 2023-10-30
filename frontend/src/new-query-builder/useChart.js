import { getChartResource } from '@/query/useChart'
import { areDeeplyEqual } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import { watchDebounced } from '@vueuse/core'
import { computed, reactive, ref, watch } from 'vue'

export default async function useChart(query) {
	const chartName = await query.getChartName()
	const chartResource = getChartResource(chartName)
	await chartResource.get.fetch()

	const chartDoc = computed({
		get: () => chartResource.doc,
		set: (val) => (chartResource.doc = val),
	})
	const chartData = ref([])
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
			chartResource.doc.options.title = query.doc.title
			chartResource.doc.options.query = query.doc.name
			chartResource.doc.options = {
				...chartResource.doc.options,
				...recommendedChart?.options,
			}
		},
		{ immediate: true, deep: true }
	)

	function getFieldsToWatch() {
		if (!chartResource.doc) return
		return {
			title: chartResource.doc.title,
			chart_type: chartResource.doc.chart_type,
			options: chartResource.doc.options,
		}
	}

	function saveIfChanged(newVal) {
		if (!newVal) return
		const oldVal = {
			title: chartResource.originalDoc.title,
			chart_type: chartResource.originalDoc.chart_type,
			options: chartResource.originalDoc.options,
		}
		if (areDeeplyEqual(newVal, oldVal)) return
		chartResource.setValue.submit({ ...newVal })
	}

	watchDebounced(getFieldsToWatch, saveIfChanged, { deep: true, debounce: 1000 })

	return {
		doc: chartDoc,
		data: chartData,
	}
}
