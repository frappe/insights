import { getChartResource } from '@/query/useChart'
import { areDeeplyEqual, createTaskRunner } from '@/utils'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import { debounce } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

export default async function useChart(query) {
	const chartName = await query.getChartName()
	const chartResource = getChartResource(chartName)
	await chartResource.get.fetch()

	const chartData = ref([])

	const run = createTaskRunner()
	async function updateDoc(doc) {
		const newValues = {
			title: doc.title,
			chart_type: doc.chart_type,
			options: doc.options,
		}
		const oldValues = {
			title: chartResource.originalDoc.title,
			chart_type: chartResource.originalDoc.chart_type,
			options: chartResource.originalDoc.options,
		}
		if (areDeeplyEqual(newValues, oldValues)) return
		await run(() =>
			chartResource.setValue.submit({
				title: doc.title,
				chart_type: doc.chart_type,
				options: doc.options,
			})
		)
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

	return {
		doc: computed({
			get: () => chartResource.doc,
			set: (value) => (chartResource.doc = value),
		}),
		data: chartData,
		updateDoc: debounce(updateDoc, 500),
	}
}
