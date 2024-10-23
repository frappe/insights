<script setup lang="ts">
import { computed, ref } from 'vue'
import { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { Chart } from '../chart'
import {
	getBarChartOptions,
	getDonutChartOptions,
	getFunnelChartOptions,
	getLineChartOptions,
} from '../helpers'
import BaseChart from './BaseChart.vue'
import DrillDown from './DrillDown.vue'
import NumberChart from './NumberChart.vue'
import TableChart from './TableChart.vue'
import ChartSectionEmptySvg from '@/query/ChartSectionEmptySvg.vue'

const props = defineProps<{ chart: Chart; showDownload?: boolean }>()
const chart = props.chart

if (!props.chart.dataQuery.result.executedSQL) {
	chart.refresh()
}

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

const drillOn = ref<{ row: QueryResultRow; column: QueryResultColumn } | null>(null)
function onClick(params: any) {
	if (params.componentType === 'series') {
		const seriesIndex = params.seriesIndex
		const dataIndex = params.dataIndex
		const row = chart.dataQuery.result.formattedRows[dataIndex]
		const column = chart.dataQuery.result.columns.find((c) => c.name === params.seriesName)!
		if (!row || !column) return
		drillOn.value = { row, column }
	}
}
</script>

<template>
	<div class="relative h-full w-full">
		<BaseChart
			v-if="eChartOptions"
			class="rounded bg-white py-1 shadow"
			:title="chart.doc.title"
			:options="eChartOptions"
			:onClick="onClick"
		/>
		<NumberChart v-if="chart.doc.chart_type == 'Number'" :chart="chart" />
		<TableChart v-if="chart.doc.chart_type == 'Table'" :chart="chart" />

		<div class="flex h-full flex-1 flex-col items-center justify-center">
			<ChartSectionEmptySvg></ChartSectionEmptySvg>
			<p class="text-gray-500">
				Pick a chart type and configure options to see the chart here
			</p>
		</div>
	</div>

	<DrillDown v-if="drillOn" :chart="chart" :row="drillOn.row" :column="drillOn.column" />
</template>
