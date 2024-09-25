<script setup lang="ts">
import { computed, ref } from 'vue'
import { downloadImage } from '../../helpers'
import { Chart } from '../chart'
import {
	getBarChartOptions,
	getDonutChartOptions,
	getFunnelChartOptions,
	getLineChartOptions,
} from '../helpers'
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
		return getDonutChartOptions(chart)
	}
	if (chart.doc.chart_type === 'Funnel') {
		return getFunnelChartOptions(chart)
	}
})
</script>

<template>
	<div class="relative h-full w-full">
		<BaseChart
			v-if="eChartOptions"
			class="rounded bg-white py-1 shadow"
			:title="chart.doc.title"
			:options="eChartOptions"
		/>
		<NumberChart v-if="chart.doc.chart_type == 'Number'" :chart="chart" />
		<TableChart v-if="chart.doc.chart_type == 'Table'" :chart="chart" />
	</div>
</template>
