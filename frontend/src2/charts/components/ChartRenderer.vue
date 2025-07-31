<script setup lang="ts">
import ChartSectionEmptySvg from '@/query/ChartSectionEmptySvg.vue'
import { computed, ref } from 'vue'
import { EMPTY_RESULT, Query } from '../../query/query'
import {
	BarChartConfig,
	DonutChartConfig,
	FunnelChartConfig,
	LineChartConfig,
	NumberChartConfig,
} from '../../types/chart.types'
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
	() =>
		!props.chart.isloaded || !props.chart.dataQuery.isloaded || props.chart.dataQuery.executing
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

const showDrillDown = ref(false)
const drillDownQuery = ref<Query>()
function onChartElementClick(params: any) {
	if (params.componentType === 'series') {
		let seriesIndex = params.seriesIndex
		let dataIndex = params.dataIndex
		if (chart_type.value === 'Row') {
			dataIndex = result.value.formattedRows.length - 1 - dataIndex
		}
		const row = result.value.formattedRows[dataIndex]
		const column = result.value.columns.find((c) => c.name === params.seriesName)!
		drillDownQuery.value = props.chart.dataQuery.getDrillDownQuery(column, row)
	}
	if (drillDownQuery.value) {
		showDrillDown.value = true
	}
}

function onNumberChartDrillDown(column: any, row: any) {
	drillDownQuery.value = props.chart.dataQuery.getDrillDownQuery(column, row)
	if (drillDownQuery.value) {
		showDrillDown.value = true
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
			:onClick="onChartElementClick"
		/>
		<NumberChart
			v-else-if="!loading && chart_type == 'Number'"
			:config="(config as NumberChartConfig)"
			:result="result"
			@drill-down="onNumberChartDrillDown"
		/>
		<TableChart v-else-if="!loading && chart_type == 'Table'" :chart="props.chart" />

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
		v-if="drillDownQuery"
		v-model="showDrillDown"
		@update:modelValue="!$event ? (drillDownQuery = undefined) : undefined"
		:query="drillDownQuery"
	>
	</DrillDown>
</template>
