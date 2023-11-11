<script setup>
import widgets from '@/widgets/widgets'
import { computed, inject, reactive } from 'vue'
import ChartActionButtons from './ChartActionButtons.vue'
import ChartSectionEmptySvg from './ChartSectionEmptySvg.vue'
import ChartTypeSelector from './ChartTypeSelector.vue'

const query = inject('query')

const showChart = computed(() => {
	return (
		query.chart.doc?.name &&
		query.formattedResults?.length &&
		query.doc.status !== 'Pending Execution'
	)
})

const emptyMessage = computed(() => {
	if (query.doc.status == 'Pending Execution') {
		return 'Execute the query to see the chart'
	}
	if (!query.formattedResults?.length) {
		return 'No results found'
	}
	return 'Pick a chart type to get started'
})

function getChartComponent() {
	if (query.chart.doc.chart_type == 'Auto') {
		const guessedChart = query.chart.getGuessedChart()
		return widgets.getComponent(guessedChart.chart_type)
	}
	return widgets.getComponent(query.chart.doc.chart_type)
}
function getChartOptions() {
	if (query.chart.doc.chart_type == 'Auto') {
		const guessedChart = query.chart.getGuessedChart()
		return guessedChart.options
	}
	return query.chart.doc.options
}
</script>

<template>
	<div v-if="query.chart.doc?.name" class="flex flex-1 flex-col gap-4 overflow-hidden">
		<div
			v-if="!showChart"
			class="flex flex-1 flex-col items-center justify-center rounded border"
		>
			<ChartSectionEmptySvg></ChartSectionEmptySvg>
			<span class="text-gray-500">{{ emptyMessage }}</span>
		</div>
		<template v-else>
			<div class="flex w-full flex-shrink-0 justify-between">
				<ChartTypeSelector></ChartTypeSelector>
				<ChartActionButtons></ChartActionButtons>
			</div>
			<div class="flex w-full flex-1 overflow-hidden rounded border">
				<component
					v-if="query.chart.doc.chart_type"
					ref="widget"
					:key="JSON.stringify(query.chart.doc)"
					:is="getChartComponent()"
					:options="getChartOptions()"
					:data="query.chart.data"
				/>
			</div>
		</template>
	</div>
</template>
