<script setup lang="ts">
import { useMagicKeys, watchDebounced, whenever } from '@vueuse/core'
import { Badge } from 'frappe-ui'
import { Copy, ImageDown, RefreshCcw, Share2, XIcon } from 'lucide-vue-next'
import { onBeforeUnmount, provide, ref } from 'vue'
import InlineFormControlLabel from '../components/InlineFormControlLabel.vue'
import { downloadImage, waitUntil } from '../helpers'
import { DropdownOption } from '../types/query.types'
import useChart from './chart'
import ChartBuilderTable from './components/ChartBuilderTable.vue'
import ChartConfigForm from './components/ChartConfigForm.vue'
import ChartFilterConfig from './components/ChartFilterConfig.vue'
import ChartQuerySelector from './components/ChartQuerySelector.vue'
import ChartRenderer from './components/ChartRenderer.vue'
import ChartShareDialog from './components/ChartShareDialog.vue'
import ChartSortConfig from './components/ChartSortConfig.vue'
import ChartTypeSelector from './components/ChartTypeSelector.vue'
import CollapsibleSection from './components/CollapsibleSection.vue'
import LazyTextInput from '../components/LazyTextInput.vue'

const props = defineProps<{ chart_name: string; queries: DropdownOption[] }>()

const chart = useChart(props.chart_name)
provide('chart', chart)
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
		<div class="relative flex h-full w-full flex-col gap-4 overflow-hidden p-3 pt-4">
			<div
				ref="chartEl"
				class="flex min-h-[24rem] flex-1 flex-shrink-0 items-center justify-center"
			>
				<ChartRenderer :chart="chart" />
			</div>
			<ChartBuilderTable v-if="chart.dataQuery.result.executedSQL" />
		</div>
		<div
			class="relative z-[1] mt-1 flex w-[19rem] flex-shrink-0 flex-col divide-y overflow-y-auto bg-white px-3.5"
		>
			<CollapsibleSection title="Chart">
				<div class="flex flex-col gap-3">
					<ChartTypeSelector v-model="chart.doc.chart_type" />
					<ChartQuerySelector v-model="chart.doc.query" :queries="props.queries" />
					<InlineFormControlLabel label="Title">
						<LazyTextInput
							type="text"
							placeholder="Title"
							v-model="chart.doc.title"
						/>
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

			<CollapsibleSection title="Actions" class="!border-b">
				<div class="flex flex-col gap-2">
					<Button v-if="!chart.doc.read_only" @click="chart.resetConfig" class="w-full">
						<template #prefix>
							<XIcon class="h-4 text-gray-700" stroke-width="1.5" />
						</template>
						Reset Options
					</Button>

					<Button @click="chart.refresh({ force: true })" class="w-full">
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

					<Button
						v-if="!chart.doc.read_only"
						class="w-full"
						@click="showShareDialog = true"
					>
						<template #prefix>
							<Share2 class="h-4 text-gray-700" stroke-width="1.5" />
						</template>
						Share Chart
					</Button>
					<Button class="w-full" @click="chart.copy">
						<template #prefix>
							<Copy class="h-4 text-gray-700" stroke-width="1.5" />
						</template>
						Copy JSON
					</Button>
				</div>
			</CollapsibleSection>
		</div>
	</div>

	<ChartShareDialog v-model="showShareDialog" :chart="chart" />
</template>
