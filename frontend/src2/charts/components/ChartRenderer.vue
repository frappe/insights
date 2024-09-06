<script setup lang="ts">
import { computed, ref } from 'vue'
import { downloadImage } from '../../helpers'
import { Chart } from '../chart'
import { getBarChartOptions, getDonutChartOptions, getLineChartOptions } from '../helpers'
import BaseChart from './BaseChart.vue'
import NumberChart from './NumberChart.vue'
import TableChart from './TableChart.vue'

const props = defineProps<{ chart: Chart; showDownload?: boolean }>()
const chart = props.chart

const eChartOptions = computed(() => {
	if (!chart.dataQuery.result.columns?.length) return
	if (chart.doc.chart_type === 'Bar') {
		return getBarChartOptions(chart)
	}
	if (chart.doc.chart_type === 'Line') {
		return getLineChartOptions(chart)
	}
	if (chart.doc.chart_type === 'Donut') {
		return getDonutChartOptions(
			chart.dataQuery.result.columns,
			chart.dataQuery.result.formattedRows
		)
	}
})

const chartEl = ref<HTMLElement | null>(null)
function downloadChart() {
	if (!chartEl.value || !chartEl.value.clientHeight) {
		console.log(chartEl.value)
		console.warn('Chart element not found')
		return
	}
	return downloadImage(chartEl.value, chart.doc.title, 2, {
		filter: (element: HTMLElement) => {
			return !element?.classList?.contains('absolute')
		},
	})
}
</script>

<template>
	<div ref="chartEl" class="relative h-full w-full">
		<BaseChart
			v-if="eChartOptions"
			class="rounded bg-white py-1 shadow"
			:title="chart.doc.title"
			:options="eChartOptions"
		/>
		<NumberChart v-if="chart.doc.chart_type == 'Number'" :chart="chart" />
		<TableChart v-if="chart.doc.chart_type == 'Table'" :chart="chart" />

		<div v-if="props.showDownload && chartEl && eChartOptions" class="absolute top-3 right-3">
			<Button variant="outline" icon="download" @click="downloadChart"></Button>
		</div>
	</div>
</template>
