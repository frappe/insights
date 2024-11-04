<script setup lang="ts">
import ChartSectionEmptySvg from '@/query/ChartSectionEmptySvg.vue'
import { computed, ref } from 'vue'
import {
	BarChartConfig,
	ChartType,
	DountChartConfig,
	FunnelChartConfig,
	LineChartConfig,
	NumberChartConfig,
} from '../../types/chart.types'
import { Operation, QueryResult, QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { WorkbookChart } from '../../types/workbook.types'
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

const props = defineProps<{
	title: string
	chart_type: ChartType
	config: WorkbookChart['config']
	operations: Operation[]
	use_live_connection?: boolean
	result: QueryResult
	loading?: boolean
}>()

const eChartOptions = computed(() => {
	if (!props.result.columns?.length) return
	if (props.chart_type === 'Bar' || props.chart_type === 'Row') {
		return getBarChartOptions(
			props.config as BarChartConfig,
			props.result,
			props.chart_type === 'Row'
		)
	}
	if (props.chart_type === 'Line') {
		return getLineChartOptions(props.config as LineChartConfig, props.result)
	}
	if (props.chart_type === 'Donut') {
		return getDonutChartOptions(props.config as DountChartConfig, props.result)
	}
	if (props.chart_type === 'Funnel') {
		return getFunnelChartOptions(props.config as FunnelChartConfig, props.result)
	}
})

const drillOn = ref<{ row: QueryResultRow; column: QueryResultColumn } | null>(null)
function onClick(params: any) {
	if (params.componentType === 'series') {
		const seriesIndex = params.seriesIndex
		const dataIndex = params.dataIndex
		const row = props.result.formattedRows[dataIndex]
		const column = props.result.columns.find((c) => c.name === params.seriesName)!
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
			v-if="!props.loading && eChartOptions"
			class="rounded bg-white py-1 shadow"
			:title="props.title"
			:options="eChartOptions"
			:onClick="onClick"
		/>
		<NumberChart
			v-else-if="!props.loading && props.chart_type == 'Number'"
			:config="(props.config as NumberChartConfig)"
			:result="props.result"
		/>
		<TableChart
			v-else-if="!props.loading && props.chart_type == 'Table'"
			:title="props.title"
			:config="props.config"
			:result="props.result"
		/>

		<div v-else class="flex h-full flex-1 flex-col items-center justify-center rounded border">
			<template v-if="props.loading">
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
		v-if="drillOn"
		:chart="{
			operations: props.operations,
			use_live_connection: props.use_live_connection,
			result: props.result,
		}"
		:row="drillOn.row"
		:column="drillOn.column"
	/>
</template>
