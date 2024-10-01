<script setup lang="ts">
import { useMagicKeys, watchDebounced, whenever } from '@vueuse/core'
import { ImageDown, RefreshCcw } from 'lucide-vue-next'
import { onBeforeUnmount, provide, ref } from 'vue'
import InlineFormControlLabel from '../components/InlineFormControlLabel.vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { downloadImage } from '../helpers'
import { WorkbookChart, WorkbookQuery } from '../types/workbook.types'
import useChart from './chart'
import ChartBuilderTable from './components/ChartBuilderTable.vue'
import ChartConfigForm from './components/ChartConfigForm.vue'
import ChartFilterConfig from './components/ChartFilterConfig.vue'
import ChartQuerySelector from './components/ChartQuerySelector.vue'
import ChartRenderer from './components/ChartRenderer.vue'
import ChartSortConfig from './components/ChartSortConfig.vue'
import ChartTypeSelector from './components/ChartTypeSelector.vue'
import CollapsibleSection from './components/CollapsibleSection.vue'

const props = defineProps<{ chart: WorkbookChart; queries: WorkbookQuery[] }>()

const chart = useChart(props.chart)
provide('chart', chart)
window.chart = chart

chart.refresh()
if (chart.doc.query && !chart.baseQuery.result.rows.length) {
	chart.baseQuery.execute()
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

const chartEl = ref<HTMLElement | null>(null)
function downloadChart() {
	if (!chartEl.value || !chartEl.value.clientHeight) {
		console.log(chartEl.value)
		console.warn('Chart element not found')
		return
	}
	return downloadImage(chartEl.value, chart.doc.title, 2, {
		filter: (element: HTMLElement) => {
			return !element?.classList?.contains('absolute')
		},
	})
}
</script>

<template>
	<div v-if="chart" class="relative flex h-full w-full overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<LoadingOverlay v-if="chart.dataQuery.executing" />
			<div
				ref="chartEl"
				class="flex min-h-[24rem] flex-1 flex-shrink-0 items-center justify-center overflow-hidden p-4"
			>
				<ChartRenderer :chart="chart" />
			</div>
			<ChartBuilderTable />
		</div>
		<div
			class="relative z-[1] flex w-[17rem] flex-shrink-0 flex-col divide-y overflow-y-auto bg-white shadow"
		>
			<CollapsibleSection title="Chart">
				<div class="flex flex-col gap-3">
					<ChartTypeSelector v-model="chart.doc.chart_type" />
					<ChartQuerySelector v-model="chart.doc.query" :queries="props.queries" />
					<InlineFormControlLabel label="Title">
						<FormControl v-model="chart.doc.title" />
					</InlineFormControlLabel>
				</div>
			</CollapsibleSection>

			<ChartConfigForm v-if="chart.doc.query" :chart="chart" />

			<CollapsibleSection title="Filter" collapsed>
				<ChartFilterConfig
					v-model="chart.doc.config.filters"
					:column-options="chart.baseQuery.result?.columnOptions || []"
				/>
			</CollapsibleSection>

			<CollapsibleSection title="Sort" collapsed>
				<ChartSortConfig
					v-model="chart.doc.config.order_by"
					:column-options="chart.dataQuery.result?.columnOptions || []"
				/>
			</CollapsibleSection>

			<CollapsibleSection title="Limit" collapsed>
				<FormControl v-model="chart.doc.config.limit" type="number" />
			</CollapsibleSection>

			<CollapsibleSection title="Actions" class="!border-b">
				<div class="flex flex-col gap-2">
					<Button @click="chart.refresh([], true)" class="w-full">
						<template #prefix>
							<RefreshCcw class="h-4 text-gray-700" stroke-width="1.5" />
						</template>
						Refresh Chart
					</Button>

					<Button class="w-full" :disabled="!chartEl" @click="downloadChart">
						<template #prefix>
							<ImageDown class="h-4 text-gray-700" stroke-width="1.5" />
						</template>
						Export as PNG
					</Button>
				</div>
			</CollapsibleSection>
		</div>
	</div>
</template>
