<script setup lang="ts">
import { ref } from 'vue'
import { Chart, getCachedChart } from '../charts/chart'
import { WorkbookChart, WorkbookDashboard } from '../workbook/workbook'
import ChartSelectorDialog from './ChartSelectorDialog.vue'
import VueGridLayout from './VueGridLayout.vue'
import useDashboard from './dashboard'
import ChartRenderer from '../charts/components/ChartRenderer.vue'

const props = defineProps<{
	dashboard: WorkbookDashboard
	charts: WorkbookChart[]
}>()
const dashboard = useDashboard(props.dashboard)

const showChartSelectorDialog = ref(false)
const showFilterCreationDialog = ref(false)
const showTextWidgetCreationDialog = ref(false)
async function valuesProvider(column_name: string, searchTxt?: string) {
	return []
}
function getItem(index: number) {
	return dashboard.doc.items[index]
}
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div class="flex h-16 items-center justify-between border-b bg-white px-4">
				<div class="text-lg font-semibold">{{ dashboard.doc.name }}</div>
				<div class="flex gap-2">
					<Button variant="outline" @click="dashboard.refresh" icon-left="refresh-ccw">
						Refresh
					</Button>
					<Dropdown
						placement="right"
						:button="{
							iconLeft: 'plus',
							variant: 'outline',
							label: 'Add Widget',
						}"
						:options="[
							{
								icon: 'bar-chart-2',
								label: 'Chart',
								onClick: () => (showChartSelectorDialog = true),
							},
							{
								icon: 'filter',
								label: 'Filter',
								onClick: () => {},
							},
							{
								icon: 'type',
								label: 'Text',
								onClick: () => {},
							},
						]"
					/>
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
						<div class="flex h-full w-full p-1.5">
							<div class="h-full w-full rounded bg-white shadow">
								<ChartRenderer
									v-if="getItem(index).type == 'chart'"
									:chart="(getCachedChart(getItem(index).chart) as Chart)"
								/>
							</div>
						</div>
					</template>
				</VueGridLayout>
			</div>
		</div>
	</div>

	<ChartSelectorDialog
		v-model="showChartSelectorDialog"
		:options="props.charts"
		@select="dashboard.addChart($event)"
	/>
</template>
