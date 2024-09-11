<script setup lang="ts">
import { useMagicKeys, watchDebounced, whenever } from '@vueuse/core'
import { onBeforeUnmount, provide } from 'vue'
import InlineFormControlLabel from '../components/InlineFormControlLabel.vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { WorkbookChart, WorkbookQuery } from '../types/workbook.types'
import useChart from './chart'
import ChartBuilderTable from './components/ChartBuilderTable.vue'
import ChartConfigForm from './components/ChartConfigForm.vue'
import ChartFilterConfig from './components/ChartFilterConfig.vue'
import ChartQuerySelector from './components/ChartQuerySelector.vue'
import ChartRenderer from './components/ChartRenderer.vue'
import ChartSortConfig from './components/ChartSortConfig.vue'
import ChartTypeSelector from './components/ChartTypeSelector.vue'
import { RefreshCcw } from 'lucide-vue-next'

const props = defineProps<{ chart: WorkbookChart; queries: WorkbookQuery[] }>()

const chart = useChart(props.chart)
provide('chart', chart)
window.chart = chart
chart.refresh()

if (!chart.doc.config.order_by) {
	chart.doc.config.order_by = []
}

watchDebounced(
	() => chart.doc.config,
	() => chart.refresh(),
	{
		deep: true,
		debounce: 500,
	}
)

const keys = useMagicKeys()
const cmdZ = keys['Meta+Z']
const cmdShiftZ = keys['Meta+Shift+Z']
const stopUndoWatcher = whenever(cmdZ, () => chart.history.undo())
const stopRedoWatcher = whenever(cmdShiftZ, () => chart.history.redo())

onBeforeUnmount(() => {
	stopUndoWatcher()
	stopRedoWatcher()
})
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<LoadingOverlay v-if="chart.dataQuery.executing" />
			<div
				class="flex min-h-[24rem] flex-1 flex-shrink-0 items-center justify-center overflow-hidden p-5"
			>
				<ChartRenderer :chart="chart" :show-download="true" />
			</div>
			<ChartBuilderTable />
		</div>
		<div
			class="relative flex w-[17rem] flex-shrink-0 flex-col gap-2.5 overflow-y-auto bg-white p-3"
		>
			<ChartQuerySelector v-model="chart.doc.query" :queries="props.queries" />
			<hr class="border-t border-gray-200" />
			<ChartTypeSelector v-model="chart.doc.chart_type" />
			<ChartConfigForm v-if="chart.doc.query" :chart="chart" />
			<hr class="border-t border-gray-200" />
			<ChartFilterConfig
				v-model="chart.doc.config.filters"
				:column-options="chart.baseQuery.result?.columnOptions || []"
			/>
			<hr class="border-t border-gray-200" />
			<ChartSortConfig
				v-model="chart.doc.config.order_by"
				:column-options="chart.dataQuery.result?.columnOptions || []"
			/>
			<hr class="border-t border-gray-200" />
			<InlineFormControlLabel label="Limit" class="!w-1/2">
				<FormControl v-model="chart.doc.config.limit" type="number" />
			</InlineFormControlLabel>
			<hr class="border-t border-gray-200" />
			<div>
				<Button @click="chart.refresh([], true)" class="w-full">
					<template #prefix>
						<RefreshCcw class="h-4 text-gray-700" stroke-width="1.5" />
					</template>
					Refresh Chart
				</Button>
			</div>
		</div>
	</div>
</template>
