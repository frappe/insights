<script setup>
import { downloadImage } from '@/utils'
import widgets from '@/widgets/widgets'
import { computed, inject, ref } from 'vue'
import ChartActionButtons from './ChartActionButtons.vue'
import ChartSectionEmptySvg from './ChartSectionEmptySvg.vue'
import ChartTypeSelector from './ChartTypeSelector.vue'

const query = inject('query')
const chartRef = ref(null)

const showChart = computed(() => {
	return (
		query.chart.doc?.name &&
		query.results.formattedResults?.length &&
		query.doc.status !== 'Pending Execution'
	)
})

const emptyMessage = computed(() => {
	if (query.doc.status == 'Pending Execution') {
		return 'Execute the query to see the chart'
	}
	if (!query.results.formattedResults?.length) {
		return 'No results found'
	}
	return 'Pick a chart type to get started'
})

const chart = computed(() => {
	const chart_type = query.chart.doc.chart_type
	const guessedChart = query.chart.getGuessedChart(chart_type)
	if (!guessedChart) return {}
	const options = Object.assign({}, guessedChart.options, query.chart.doc.options)
	return {
		type: guessedChart.chart_type,
		data: query.chart.data,
		options: chart_type == 'Auto' ? guessedChart.options : options,
		component: widgets.getComponent(guessedChart.chart_type),
	}
})

const fullscreenDialog = ref(false)
function showInFullscreenDialog() {
	fullscreenDialog.value = true
}
const downloading = ref(false)
function downloadChartImage() {
	if (!chartRef.value) {
		$notify({
			variant: 'error',
			title: 'Chart container reference not found',
		})
		return
	}
	downloading.value = true
	const title = query.chart.doc.options.title || query.doc.title
	downloadImage(chartRef.value.$el, `${title}.png`).then(() => {
		downloading.value = false
	})
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
				<ChartActionButtons @fullscreen="showInFullscreenDialog"></ChartActionButtons>
			</div>
			<div class="flex w-full flex-1 overflow-hidden rounded border">
				<component
					v-if="chart.type"
					:is="chart.component"
					:options="chart.options"
					:data="chart.data"
					:key="JSON.stringify(query.chart.doc) + JSON.stringify(query.chart.data)"
				/>
			</div>
		</template>

		<Dialog
			v-if="chart.type"
			v-model="fullscreenDialog"
			:options="{
				size: '7xl',
			}"
		>
			<template #body>
				<div class="relative flex h-[40rem] w-full p-1">
					<component
						v-if="chart.type"
						ref="chartRef"
						:is="chart.component"
						:options="chart.options"
						:data="chart.data"
						:key="JSON.stringify(query.chart.doc)"
					/>
					<div class="absolute top-0 right-0 p-2">
						<Button
							variant="outline"
							@click="downloadChartImage"
							:loading="downloading"
							icon="download"
						>
						</Button>
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>
