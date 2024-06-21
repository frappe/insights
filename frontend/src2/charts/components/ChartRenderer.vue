<script setup lang="ts">
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { Chart } from '../chart'
import {
	getBarChartOptions,
	getDonutChartOptions,
	getLineChartOptions,
	getRowChartOptions,
} from '../helpers'
import NumberChart from './NumberChart.vue'

const props = defineProps<{ chart: Chart }>()
const chart = props.chart

const eChartOptions = computed(() => {
	if (!chart.dataQuery.result.columns?.length) return
	if (chart.doc.chart_type === 'Bar') {
		return getBarChartOptions(
			chart.dataQuery.result.columns,
			chart.dataQuery.result.formattedRows
		)
	}
	if (chart.doc.chart_type === 'Line') {
		return getLineChartOptions(
			chart.dataQuery.result.columns,
			chart.dataQuery.result.formattedRows
		)
	}
	if (chart.doc.chart_type === 'Row') {
		return getRowChartOptions(
			chart.dataQuery.result.columns,
			chart.dataQuery.result.formattedRows
		)
	}
	if (chart.doc.chart_type === 'Donut') {
		return getDonutChartOptions(
			chart.dataQuery.result.columns,
			chart.dataQuery.result.formattedRows
		)
	}
})
</script>

<template>
	<BaseChart v-if="eChartOptions" class="p-2" :options="eChartOptions" />
	<div v-if="chart.doc.chart_type == 'Number'" class="h-full w-full">
		<NumberChart :chart="chart" />
	</div>
	<DataTable
		v-if="chart.doc.chart_type == 'Table'"
		:columns="chart.dataQuery.result.columns"
		:rows="chart.dataQuery.result.rows"
	/>
</template>
