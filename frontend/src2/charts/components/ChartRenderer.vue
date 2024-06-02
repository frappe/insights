<script setup lang="ts">
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import { Chart } from '../chart'
import DataTable from '../../components/DataTable.vue'
import MetricChart from './MetricChart.vue'
import {
	getBarChartOptions,
	getDonutChartOptions,
	getLineChartOptions,
	getRowChartOptions,
} from '../helpers'

const props = defineProps<{ chart: Chart }>()
const chart = props.chart

const eChartOptions = computed(() => {
	if (!chart.dataQuery.result.columns?.length) return
	if (chart.doc.type === 'Bar') {
		return getBarChartOptions(chart.dataQuery.result.columns, chart.dataQuery.result.rows)
	}
	if (chart.doc.type === 'Line') {
		return getLineChartOptions(chart.dataQuery.result.columns, chart.dataQuery.result.rows)
	}
	if (chart.doc.type === 'Row') {
		return getRowChartOptions(chart.dataQuery.result.columns, chart.dataQuery.result.rows)
	}
	if (chart.doc.type === 'Donut') {
		return getDonutChartOptions(chart.dataQuery.result.columns, chart.dataQuery.result.rows)
	}
})
</script>

<template>
	<BaseChart v-if="eChartOptions" class="min-h-[20rem] p-2" :options="eChartOptions" />
	<div v-if="chart.doc.type == 'Metric'" class="rounded border">
		<MetricChart :chart="chart" />
	</div>
	<DataTable
		v-if="chart.doc.type == 'Table'"
		:columns="chart.dataQuery.result.columns"
		:rows="chart.dataQuery.result.rows"
	/>
</template>
