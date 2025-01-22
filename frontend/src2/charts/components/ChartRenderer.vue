<script setup lang="ts">
import ChartSectionEmptySvg from '@/query/ChartSectionEmptySvg.vue'
import { computed, ref } from 'vue'
import { EMPTY_RESULT } from '../../query/query'
import {
	BarChartConfig,
	DonutChartConfig,
	FunnelChartConfig,
	LineChartConfig,
	NumberChartConfig,
} from '../../types/chart.types'
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

const props = defineProps<{ chart: Chart }>()

const chart_type = computed(() => props.chart.doc.chart_type)
const config = computed(() => props.chart.doc.config)
const result = computed(() => props.chart.dataQuery.result || { ...EMPTY_RESULT })
const loading = computed(
	() => props.chart.loading || props.chart.dataQuery.loading || props.chart.dataQuery.executing
)

const eChartOptions = computed(() => {
	if (!result.value.columns?.length) return
	if (chart_type.value === 'Bar' || chart_type.value === 'Row') {
		return getBarChartOptions(
			config.value as BarChartConfig,
			result.value,
			chart_type.value === 'Row'
		)
	}
	if (chart_type.value === 'Line') {
		return getLineChartOptions(config.value as LineChartConfig, result.value)
	}
	if (chart_type.value === 'Donut') {
		return getDonutChartOptions(config.value as DonutChartConfig, result.value)
	}
	if (chart_type.value === 'Funnel') {
		return getFunnelChartOptions(config.value as FunnelChartConfig, result.value)
	}
})

const drillOn = ref<{ row: QueryResultRow; column: QueryResultColumn } | null>(null)
function onClick(params: any) {
	if (!result.value) return
	if (params.componentType === 'series') {
		const seriesIndex = params.seriesIndex
		const dataIndex = params.dataIndex
		const row = result.value.formattedRows[dataIndex]
		const column = result.value.columns.find((c) => c.name === params.seriesName)!
		if (!row || !column) {
			drillOn.value = null
			return
		}
		drillOn.value = { row, column }
	}
}
</script>

<template>
	<div class="relative h-full w-full">
		<BaseChart
			v-if="!loading && eChartOptions"
			class="rounded bg-white py-1 shadow"
			:title="props.chart.doc.title"
			:options="eChartOptions"
			:onClick="onClick"
		/>
		<NumberChart
			v-else-if="!loading && chart_type == 'Number'"
			:config="(config as NumberChartConfig)"
			:result="result"
		/>
		<TableChart
			v-else-if="!loading && chart_type == 'Table'"
			:title="props.chart.doc.title"
			:config="config"
			:result="result"
		/>

		<div v-else class="flex h-full flex-1 flex-col items-center justify-center rounded border">
			<template v-if="loading">
				<LoadingIndicator class="h-5 w-5 text-gray-500" />
				<p class="mt-1.5 text-gray-500">Loading data...</p>
			</template>
			<template v-else>
				<ChartSectionEmptySvg></ChartSectionEmptySvg>
				<p class="text-gray-500">
					Pick a chart type and configure options to see the chart here
				</p>
			</template>
		</div>
	</div>

	<DrillDown
		v-if="drillOn && !loading"
		:chart="{
			operations: props.chart.dataQuery.doc.operations,
			use_live_connection: props.chart.dataQuery.doc.use_live_connection,
			result: result,
		}"
		:row="drillOn.row"
		:column="drillOn.column"
		@close="drillOn = null"
	/>
</template>
