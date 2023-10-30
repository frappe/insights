<script setup>
import { getChartResource } from '@/query/useChart'
import { getFormattedResult } from '@/utils/query/results'
import { convertResultToObjects, guessChart } from '@/widgets/useChartData'
import widgets from '@/widgets/widgets'
import { computed, inject, ref, watch } from 'vue'
import ChartSectionEmpty from './ChartSectionEmpty.vue'

const query = inject('query')
const chartName = await query.getChartName()

const chartResource = getChartResource(chartName)
await chartResource.get.fetch()

const chartDoc = computed(() => chartResource.doc)
const chartData = ref(null)
const chartRefreshKey = ref(0)

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
		console.log('recommendedChart', recommendedChart)
		chartResource.doc.chart_type = recommendedChart?.type
		chartResource.doc.options = recommendedChart?.options
		chartResource.doc.options.title = query.doc.title
		chartResource.doc.options.query = query.doc.name
		chartRefreshKey.value++
	},
	{ immediate: true, deep: true }
)

const emptyMessage = computed(() => {
	if (query.doc.status == 'Pending Execution') {
		return 'Execute the query to see the chart'
	}
	if (!query.doc.results?.length) {
		return 'No results found'
	}
	return 'Pick a chart type to get started'
})
</script>

<template>
	<div class="flex flex-1 items-center justify-center overflow-hidden rounded border">
		<div
			v-if="
				!chartDoc?.name ||
				!query.doc?.results?.length ||
				query.doc.status == 'Pending Execution'
			"
			class="flex flex-1 flex-col items-center justify-center"
		>
			<ChartSectionEmpty></ChartSectionEmpty>
			<span class="text-gray-500">{{ emptyMessage }}</span>
		</div>
		<div v-else class="flex h-full w-full flex-1">
			<component
				v-if="chartDoc.chart_type"
				ref="widget"
				:is="widgets.getComponent(chartDoc.chart_type)"
				:data="chartData"
				:options="chartDoc.options"
				:key="chartRefreshKey"
			/>
		</div>
	</div>
</template>
