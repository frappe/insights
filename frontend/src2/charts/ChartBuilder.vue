<script setup lang="ts">
import { LoadingIndicator } from 'frappe-ui'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import { provide } from 'vue'
import DataTable from '../components/DataTable.vue'
import { WorkbookChart, WorkbookQuery } from '../workbook/workbook'
import useChart from './chart'
import AxisChartConfigForm from './components/AxisChartConfigForm.vue'
import ChartQuerySelector from './components/ChartQuerySelector.vue'
import ChartRenderer from './components/ChartRenderer.vue'
import ChartSortConfig from './components/ChartSortConfig.vue'
import ChartTypeSelector from './components/ChartTypeSelector.vue'
import DonutChartConfigForm from './components/DonutChartConfigForm.vue'
import MetricChartConfigForm from './components/MetricChartConfigForm.vue'
import TableChartConfigForm from './components/TableChartConfigForm.vue'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	DountChartConfig,
	MetricChartConfig,
	TableChartConfig,
} from './helpers'

const props = defineProps<{ chart: WorkbookChart; queries: WorkbookQuery[] }>()

const chart = useChart(props.chart)
provide('chart', chart)
chart.refresh()

if (!chart.doc.config.order_by) {
	chart.doc.config.order_by = []
}
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
				class="flex min-h-[24rem] flex-1 flex-shrink-0 items-center justify-center overflow-hidden p-5"
			>
				<div class="h-full w-full overflow-hidden rounded bg-white shadow">
					<ChartRenderer :chart="chart" />
				</div>
			</div>
			<DataTable
				v-if="chart.doc.chart_type != 'Table'"
				class="max-h-[17rem] border-x bg-white"
				:columns="chart.dataQuery.result.columns"
				:rows="chart.dataQuery.result.formattedRows"
			>
				<template #column-header="{ column }">
					<div
						class="flex cursor-pointer items-center gap-2 truncate py-2 px-3 hover:underline"
					>
						<span>{{ column.name }}</span>
						<!-- <ChevronDown
							v-if="chart.sortOrder[column.name] === 'desc'"
							class="h-4 w-4 text-gray-700"
							stroke-width="1.5"
						/>
						<ChevronUp
							v-if="chart.sortOrder[column.name] === 'asc'"
							class="h-4 w-4 text-gray-700"
							stroke-width="1.5"
						/> -->
					</div>
				</template>
			</DataTable>
		</div>
		<div class="relative flex w-[17rem] flex-shrink-0 flex-col overflow-y-auto bg-white">
			<ChartTypeSelector v-model="chart.doc.chart_type" />
			<hr class="my-1 border-t border-gray-200" />
			<ChartQuerySelector v-model="chart.doc.query" :queries="props.queries" />
			<template v-if="chart.doc.query">
				<hr class="my-1 border-t border-gray-200" />
				<MetricChartConfigForm
					v-if="chart.doc.chart_type == 'Metric'"
					v-model="(chart.doc.config as MetricChartConfig)"
					:dimensions="chart.baseQuery.dimensions"
					:measures="chart.baseQuery.measures"
				/>
				<DonutChartConfigForm
					v-if="chart.doc.chart_type == 'Donut'"
					v-model="(chart.doc.config as DountChartConfig)"
					:dimensions="chart.baseQuery.dimensions"
					:measures="chart.baseQuery.measures"
				/>
				<TableChartConfigForm
					v-if="chart.doc.chart_type == 'Table'"
					v-model="(chart.doc.config as TableChartConfig)"
					:dimensions="chart.baseQuery.dimensions"
					:measures="chart.baseQuery.measures"
				/>
				<AxisChartConfigForm
					v-if="AXIS_CHARTS.includes(chart.doc.chart_type)"
					v-model="(chart.doc.config as AxisChartConfig)"
					:chart-type="chart.doc.chart_type"
					:dimensions="chart.baseQuery.dimensions"
					:measures="chart.baseQuery.measures"
				/>
				<hr class="my-1 border-t border-gray-200" />
				<ChartSortConfig
					v-model="chart.doc.config.order_by"
					:column-options="chart.dataQuery.result.columnOptions"
				/>
			</template>
		</div>
	</div>
</template>
