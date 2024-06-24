<script setup lang="ts">
import { LoadingIndicator } from 'frappe-ui'
import { provide } from 'vue'
import DataTable from '../components/DataTable.vue'
import { WorkbookChart, WorkbookQuery } from '../types/workbook.types'
import useChart from './chart'
import ChartConfigForm from './components/ChartConfigForm.vue'
import ChartQuerySelector from './components/ChartQuerySelector.vue'
import ChartRenderer from './components/ChartRenderer.vue'
import ChartSortConfig from './components/ChartSortConfig.vue'
import ChartTypeSelector from './components/ChartTypeSelector.vue'

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
				<ChartRenderer :chart="chart" />
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
					</div>
				</template>
			</DataTable>
		</div>
		<div
			class="relative flex w-[17rem] flex-shrink-0 flex-col gap-2.5 overflow-y-auto bg-white p-3"
		>
			<ChartQuerySelector v-model="chart.doc.query" :queries="props.queries" />
			<hr class="my-1 border-t border-gray-200" />
			<ChartTypeSelector v-model="chart.doc.chart_type" />
			<ChartConfigForm v-if="chart.doc.query" :chart="chart" />
			<hr class="my-1 border-t border-gray-200" />
			<ChartSortConfig
				v-model="chart.doc.config.order_by"
				:column-options="chart.dataQuery.result.columnOptions || []"
			/>
		</div>
	</div>
</template>
