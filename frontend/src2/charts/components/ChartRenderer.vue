<script setup lang="ts">
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { Chart } from '../chart'
import { getBarChartOptions, getDonutChartOptions, getLineChartOptions } from '../helpers'
import NumberChart from './NumberChart.vue'

const props = defineProps<{ chart: Chart }>()
const chart = props.chart
chart.refresh()

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
</script>

<template>
	<BaseChart
		v-if="eChartOptions"
		class="rounded bg-white py-1 shadow"
		:title="chart.doc.title"
		:options="eChartOptions"
	/>
	<NumberChart v-if="chart.doc.chart_type == 'Number'" :chart="chart" />
	<DataTable
		v-if="chart.doc.chart_type == 'Table'"
		:columns="chart.dataQuery.result.columns"
		:rows="chart.dataQuery.result.rows"
	/>
</template>
