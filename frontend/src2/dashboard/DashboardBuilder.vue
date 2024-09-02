<script setup lang="ts">
import { Edit3, RefreshCcw } from 'lucide-vue-next'
import { computed, provide, ref } from 'vue'
import { safeJSONParse } from '../helpers'
import { createToast } from '../helpers/toasts'
import { WorkbookChart, WorkbookDashboard, WorkbookQuery } from '../types/workbook.types'
import ChartSelectorDialog from './ChartSelectorDialog.vue'
import useDashboard from './dashboard'
import DashboardFilterSelector from './DashboardFilterSelector.vue'
import DashboardItem from './DashboardItem.vue'
import DashboardItemActions from './DashboardItemActions.vue'
import VueGridLayout from './VueGridLayout.vue'
import ContentEditable from '../components/ContentEditable.vue'

const props = defineProps<{
	dashboard: WorkbookDashboard
	charts: WorkbookChart[]
	queries: WorkbookQuery[]
}>()

const dashboard = useDashboard(props.dashboard)
provide('dashboard', dashboard)
dashboard.refresh()

const selectedCharts = computed(() => {
	return dashboard.doc.items.filter((item) => item.type == 'chart')
})

const showChartSelectorDialog = ref(false)
const showTextWidgetCreationDialog = ref(false)

function onDragOver(event: DragEvent) {
	if (!event.dataTransfer) return
	event.preventDefault()
	event.dataTransfer.dropEffect = 'copy'
}
function onDrop(event: DragEvent) {
	if (!event.dataTransfer) return
	event.preventDefault()
	if (!dashboard.editing && dashboard.doc.items.length > 0) {
		return createToast({
			title: 'Info',
			message: 'You can only add charts to the dashboard in edit mode',
			variant: 'info',
		})
	}
	if (!dashboard.editing) {
		dashboard.editing = true
	}
	const data = safeJSONParse(event.dataTransfer.getData('text/plain'))
	const chartName = data.item.name
	const chart = props.charts.find((c) => c.name === chartName)
	if (!chart) return
	dashboard.addChart([chart])
}
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div class="flex items-center justify-between border-x bg-white py-3 px-4 shadow-sm">
				<ContentEditable
					class="rounded-sm text-lg font-medium !text-gray-800 focus:ring-2 focus:ring-gray-700 focus:ring-offset-4"
					:class="[dashboard.editing ? '' : 'cursor-default']"
					v-model="dashboard.doc.title"
					:disabled="!dashboard.editing"
					placeholder="Untitled Dashboard"
				></ContentEditable>
				<div class="flex gap-2">
					<DashboardFilterSelector
						v-if="!dashboard.editing"
						:dashboard="dashboard"
						:queries="props.queries"
						:charts="props.charts"
					/>
					<Button
						v-if="!dashboard.editing"
						variant="outline"
						@click="() => dashboard.refresh()"
						label="Refresh"
					>
						<template #prefix>
							<RefreshCcw class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<Button
						v-if="!dashboard.editing"
						variant="outline"
						@click="dashboard.editing = true"
						label="Edit"
					>
						<template #prefix>
							<Edit3 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<Button
						v-if="dashboard.editing"
						variant="outline"
						icon-left="plus"
						@click="showChartSelectorDialog = true"
					>
						Chart
					</Button>
					<Button
						v-if="dashboard.editing"
						variant="solid"
						icon-left="check"
						@click="dashboard.editing = false"
					>
						Done
					</Button>
				</div>
			</div>
			<div class="flex-1 overflow-y-auto p-2" @dragover="onDragOver" @drop="onDrop">
				<VueGridLayout
					v-if="dashboard.doc.items.length > 0"
					class="h-fit w-full"
					:class="[dashboard.editing ? 'mb-[20rem] ' : '']"
					:cols="20"
					:disabled="!dashboard.editing"
					:modelValue="dashboard.doc.items.map((item) => item.layout)"
					@update:modelValue="
						(newLayout) => {
							dashboard.doc.items.forEach((item, idx) => {
								item.layout = newLayout[idx]
							})
						}
					"
				>
					<template #item="{ index }">
						<div class="relative h-full w-full p-2 [&>div:first-child]:h-full">
							<Popover
								class="h-full"
								:show="dashboard.editing && dashboard.isActiveItem(index)"
								placement="top-start"
							>
								<template #target>
									<DashboardItem
										:index="index"
										:item="dashboard.doc.items[index]"
									/>
								</template>
								<template #body>
									<DashboardItemActions
										:dashboard="dashboard"
										:item-index="index"
										:item="dashboard.doc.items[index]"
									/>
								</template>
							</Popover>
						</div>
					</template>
				</VueGridLayout>
			</div>
		</div>
	</div>

	<ChartSelectorDialog
		v-model="showChartSelectorDialog"
		:chartOptions="props.charts"
		:selected-charts="
			selectedCharts.map(
				(c) => props.charts.find((chart) => chart.name === c.chart) as WorkbookChart,
			)
		"
		@select="dashboard.addChart($event)"
	/>
</template>
