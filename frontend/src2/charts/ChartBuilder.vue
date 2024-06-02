<script setup lang="ts">
import { LoadingIndicator } from 'frappe-ui'
import DataTable from '../components/DataTable.vue'
import AxisChartConfigForm from './components/AxisChartConfigForm.vue'
import ChartQuerySelector from './components/ChartQuerySelector.vue'
import ChartRenderer from './components/ChartRenderer.vue'
import ChartTypeSelector from './components/ChartTypeSelector.vue'
import DonutChartConfigForm from './components/DonutChartConfigForm.vue'
import MetricChartConfigForm from './components/MetricChartConfigForm.vue'
import TableChartConfigForm from './components/TableChartConfigForm.vue'
import useChart from './chart'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	DountChartConfig,
	MetricChartConfig,
	TableChartConfig,
} from './helpers'
import { provide } from 'vue'

const props = defineProps<{ chartId: string; queries: string[] }>()
const chart = useChart(props.chartId)
provide('chart', chart)
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col divide-y overflow-hidden">
			<div
				v-if="chart.dataQuery.executing"
				class="absolute top-0 left-0 z-10 flex h-full w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
			>
				<LoadingIndicator class="h-8 w-8 text-gray-700" />
			</div>
			<div
				class="flex min-h-[24rem] flex-1 flex-shrink-0 items-center justify-center overflow-hidden p-6"
			>
				<div class="h-full w-full overflow-hidden rounded bg-white shadow">
					<ChartRenderer :chart="chart" />
				</div>
			</div>
			<DataTable
				v-if="chart.doc.type != 'Table'"
				:columns="chart.dataQuery.result.columns"
				:rows="chart.dataQuery.result.rows"
				class="max-h-[17rem] bg-white"
			/>
		</div>
		<div class="relative flex w-[17rem] flex-shrink-0 flex-col overflow-y-auto bg-white">
			<ChartTypeSelector v-model="chart.doc.type" />
			<hr class="my-1 border-t border-gray-200" />
			<ChartQuerySelector v-model="chart.doc.query" :queries="props.queries" />
			<template v-if="chart.baseQuery.doc?.name">
				<hr class="my-1 border-t border-gray-200" />
				<MetricChartConfigForm
					v-if="chart.doc.type == 'Metric'"
					v-model="(chart.doc.config as MetricChartConfig)"
					:dimensions="chart.baseQuery.dimensions"
					:measures="chart.baseQuery.measures"
				/>
				<DonutChartConfigForm
					v-if="chart.doc.type == 'Donut'"
					v-model="(chart.doc.config as DountChartConfig)"
					:dimensions="chart.baseQuery.dimensions"
					:measures="chart.baseQuery.measures"
				/>
				<TableChartConfigForm
					v-if="chart.doc.type == 'Table'"
					v-model="(chart.doc.config as TableChartConfig)"
					:dimensions="chart.baseQuery.dimensions"
					:measures="chart.baseQuery.measures"
				/>
				<AxisChartConfigForm
					v-if="AXIS_CHARTS.includes(chart.doc.type)"
					v-model="(chart.doc.config as AxisChartConfig)"
					:chart-type="chart.doc.type"
					:dimensions="chart.baseQuery.dimensions"
					:measures="chart.baseQuery.measures"
				/>
			</template>
		</div>
	</div>
</template>
