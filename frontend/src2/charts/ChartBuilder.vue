<script setup lang="ts">
import { useMagicKeys, watchDebounced, whenever } from '@vueuse/core'
import { Badge } from 'frappe-ui'
import { onBeforeUnmount, provide, ref } from 'vue'
import InlineFormControlLabel from '../components/InlineFormControlLabel.vue'
import LazyTextInput from '../components/LazyTextInput.vue'
import { downloadImage, waitUntil } from '../helpers'
import { DropdownOption } from '../types/query.types'
import useChart from './chart'
import ChartBuilderTable from './components/ChartBuilderTable.vue'
import ChartBuilderToolbar from './components/ChartBuilderToolbar.vue'
import ChartConfigForm from './components/ChartConfigForm.vue'
import ChartFilterConfig from './components/ChartFilterConfig.vue'
import ChartQuerySelector from './components/ChartQuerySelector.vue'
import ChartRenderer from './components/ChartRenderer.vue'
import ChartShareDialog from './components/ChartShareDialog.vue'
import ChartSortConfig from './components/ChartSortConfig.vue'
import ChartTypeSelector from './components/ChartTypeSelector.vue'
import CollapsibleSection from './components/CollapsibleSection.vue'

const props = defineProps<{ chart_name: string; queries: DropdownOption[] }>()

const chart = useChart(props.chart_name)
provide('chart', chart)
// @ts-ignore
window.chart = chart

await waitUntil(() => chart.isloaded)

// refresh separately to avoid debounce
chart.refresh()
watchDebounced(
	() => chart.doc.config,
	() => chart.refresh(),
	{
		deep: true,
		debounce: 500,
	},
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

const showShareDialog = ref(false)
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden">
		<div class="relative flex h-full w-full flex-col gap-3 overflow-hidden p-4">
			<ChartBuilderToolbar
				v-if="chart.doc.query"
				:chart="chart"
				:chartEl="chartEl"
				:onDownload="downloadChart"
				:onShare="() => (showShareDialog = true)"
			/>
			<div
				ref="chartEl"
				class="flex min-h-[24rem] flex-1 flex-shrink-0 items-center justify-center"
			>
				<ChartRenderer :chart="chart" />
			</div>
			<ChartBuilderTable v-if="chart.dataQuery.result.executedSQL" />
		</div>
		<div
			class="relative mt-1 flex w-[19rem] flex-shrink-0 flex-col divide-y overflow-y-auto bg-white px-3.5"
		>
			<CollapsibleSection title="Chart">
				<div class="flex flex-col gap-3">
					<ChartTypeSelector v-model="chart.doc.chart_type" />
					<ChartQuerySelector v-model="chart.doc.query" :queries="props.queries" />
					<InlineFormControlLabel label="Title">
						<LazyTextInput type="text" placeholder="Title" v-model="chart.doc.title" />
					</InlineFormControlLabel>
				</div>
			</CollapsibleSection>

			<ChartConfigForm v-if="chart.doc.query" :chart="chart" />

			<CollapsibleSection title="Filters" collapsed>
				<template #title-suffix v-if="chart.doc.config.filters?.filters.length">
					<Badge size="sm" theme="orange" type="info" class="mt-0.5">
						<span class="tnum"> {{ chart.doc.config.filters.filters.length }}</span>
					</Badge>
				</template>
				<ChartFilterConfig v-model="chart.doc.config.filters" />
			</CollapsibleSection>

			<CollapsibleSection title="Sort" collapsed>
				<template #title-suffix v-if="chart.doc.config.order_by?.length">
					<Badge size="sm" theme="orange" type="info" class="mt-0.5">
						<span class="tnum"> {{ chart.doc.config.order_by?.length }}</span>
					</Badge>
				</template>
				<ChartSortConfig
					v-model="chart.doc.config.order_by"
					:column-options="chart.dataQuery.result?.columnOptions || []"
				/>
			</CollapsibleSection>

			<CollapsibleSection title="Limit" collapsed>
				<FormControl v-model="chart.doc.config.limit" type="number" />
			</CollapsibleSection>
		</div>
	</div>

	<ChartShareDialog v-model="showShareDialog" :chart="chart" />
</template>
