<script setup lang="ts">
import { computed, ref } from 'vue'
import { Chart, getCachedChart } from '../charts/chart'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { WorkbookChart, WorkbookDashboard, WorkbookDashboardChart } from '../workbook/workbook'
import ChartSelectorDialog from './ChartSelectorDialog.vue'
import DashboardItemActions from './DashboardItemActions.vue'
import VueGridLayout from './VueGridLayout.vue'
import useDashboard from './dashboard'

const props = defineProps<{
	dashboard: WorkbookDashboard
	charts: WorkbookChart[]
}>()
const dashboard = useDashboard(props.dashboard)
const selectedCharts = computed(() => {
	return dashboard.doc.items.filter((item) => item.type == 'chart') as WorkbookDashboardChart[]
})

const showChartSelectorDialog = ref(false)
const showFilterSelectorDialog = ref(false)
const showTextWidgetCreationDialog = ref(false)
async function valuesProvider(column_name: string, searchTxt?: string) {
	return []
}
function getItem(index: number) {
	return dashboard.doc.items[index]
}
function getChart(index: number) {
	const item = getItem(index) as WorkbookDashboardChart
	return getCachedChart(item.chart) as Chart
}
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div class="flex h-16 items-center justify-between border-b bg-white px-4">
				<div class="text-lg font-semibold">{{ dashboard.doc.title }}</div>
				<div class="flex gap-2">
					<Button variant="outline" @click="dashboard.refresh" icon-left="refresh-ccw">
						Refresh
					</Button>
					<Button
						variant="outline"
						icon-left="plus"
						@click="showChartSelectorDialog = true"
					>
						Chart
					</Button>
				</div>
			</div>
			<div class="flex-1 overflow-y-auto p-3">
				<VueGridLayout
					v-if="dashboard.doc.items.length > 0"
					class="h-fit w-full"
					:class="[false ? 'mb-[20rem] ' : '']"
					:cols="12"
					:disabled="false"
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
						<div class="relative flex h-full w-full p-1.5">
							<div
								class="h-full w-full rounded bg-white shadow"
								:class="
									dashboard.activeItemIdx == index
										? 'outline outline-gray-700'
										: ''
								"
								@click="dashboard.setActiveItem(index)"
							>
								<ChartRenderer
									v-if="getItem(index).type == 'chart'"
									:chart="getChart(index)"
								/>
							</div>
							<DashboardItemActions
								class="absolute right-0 top-1 -mr-7"
								v-if="dashboard.activeItemIdx == index"
								@delete="dashboard.removeItem(index)"
							/>
						</div>
					</template>
				</VueGridLayout>
			</div>
		</div>
	</div>

	<ChartSelectorDialog
		v-model="showChartSelectorDialog"
		:chartOptions="
			props.charts.filter((chart) => !selectedCharts.some((c) => c.chart == chart.name))
		"
		@select="dashboard.addChart($event)"
	/>
</template>
