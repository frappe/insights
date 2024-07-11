<script setup lang="ts">
import { provide } from 'vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { WorkbookChart, WorkbookQuery } from '../types/workbook.types'
import useChart from './chart'
import ChartBuilderTable from './ChartBuilderTable.vue'
import ChartConfigForm from './components/ChartConfigForm.vue'
import ChartQuerySelector from './components/ChartQuerySelector.vue'
import ChartRenderer from './components/ChartRenderer.vue'
import ChartSortConfig from './components/ChartSortConfig.vue'
import ChartFilterConfig from './components/ChartFilterConfig.vue'
import ChartTypeSelector from './components/ChartTypeSelector.vue'

const props = defineProps<{ chart: WorkbookChart; queries: WorkbookQuery[] }>()

const chart = useChart(props.chart)
provide('chart', chart)

if (!chart.doc.config.order_by) {
	chart.doc.config.order_by = []
}
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<LoadingOverlay v-if="chart.dataQuery.executing" />
			<div
				class="flex min-h-[24rem] flex-1 flex-shrink-0 items-center justify-center overflow-hidden p-5"
			>
				<ChartRenderer :chart="chart" />
			</div>
			<ChartBuilderTable />
		</div>
		<div
			class="relative flex w-[17rem] flex-shrink-0 flex-col gap-2.5 overflow-y-auto bg-white p-3"
		>
			<ChartQuerySelector v-model="chart.doc.query" :queries="props.queries" />
			<hr class="my-1 border-t border-gray-200" />
			<ChartTypeSelector v-model="chart.doc.chart_type" />
			<ChartConfigForm v-if="chart.doc.query" :chart="chart" />
			<hr class="my-1 border-t border-gray-200" />
			<ChartFilterConfig
				v-model="chart.doc.config.filters"
				:column-options="chart.baseQuery.result?.columnOptions || []"
			/>
			<ChartSortConfig
				v-model="chart.doc.config.order_by"
				:column-options="chart.dataQuery.result?.columnOptions || []"
			/>
		</div>
	</div>
</template>
