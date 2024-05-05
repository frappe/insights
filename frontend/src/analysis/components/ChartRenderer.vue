<script setup lang="ts">
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import { AnalysisChart } from '../useAnalysisChart'
import DataTable from './DataTable.vue'
import MetricChart from './MetricChart.vue'
import {
	getBarChartOptions,
	getDonutChartOptions,
	getLineChartOptions,
	getRowChartOptions,
} from './chart_utils'

const props = defineProps<{ chart: AnalysisChart }>()
const analysisChart = props.chart

const eChartOptions = computed(() => {
	if (!analysisChart.query.result.columns?.length) return
	if (analysisChart.type === 'Bar') {
		return getBarChartOptions(
			analysisChart.query.result.columns,
			analysisChart.query.result.rows
		)
	}
	if (analysisChart.type === 'Line') {
		return getLineChartOptions(
			analysisChart.query.result.columns,
			analysisChart.query.result.rows
		)
	}
	if (analysisChart.type === 'Row') {
		return getRowChartOptions(
			analysisChart.query.result.columns,
			analysisChart.query.result.rows
		)
	}
	if (analysisChart.type === 'Donut') {
		return getDonutChartOptions(
			analysisChart.query.result.columns,
			analysisChart.query.result.rows
		)
	}
})
</script>

<template>
	<BaseChart v-if="eChartOptions" class="min-h-[20rem] p-2" :options="eChartOptions" />
	<div v-if="analysisChart.type == 'Metric'" class="rounded border">
		<MetricChart :chart="analysisChart" />
	</div>
	<DataTable
		v-if="analysisChart.type == 'Table'"
		:columns="analysisChart.query.result.columns"
		:rows="analysisChart.query.result.rows"
	/>
</template>
