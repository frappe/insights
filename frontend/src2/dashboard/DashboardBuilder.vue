<script setup lang="ts">
import { computed, provide, ref } from 'vue'
import {
	WorkbookChart,
	WorkbookDashboard,
	WorkbookDashboardChart,
	WorkbookQuery,
} from '../workbook/workbook'
import ChartSelectorDialog from './ChartSelectorDialog.vue'
import DashboardItemActions from './DashboardItemActions.vue'
import FilterSelectorDialog from './FilterSelectorDialog.vue'
import VueGridLayout from './VueGridLayout.vue'
import useDashboard from './dashboard'
import DashboardItem from './DashboardItem.vue'

const props = defineProps<{
	dashboard: WorkbookDashboard
	charts: WorkbookChart[]
	queries: WorkbookQuery[]
}>()

const dashboard = useDashboard(props.dashboard)
provide('dashboard', dashboard)

const selectedCharts = computed(() => {
	return dashboard.doc.items.filter((item) => item.type == 'chart') as WorkbookDashboardChart[]
})

const showChartSelectorDialog = ref(false)
const showFilterSelectorDialog = ref(false)
const showTextWidgetCreationDialog = ref(false)
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div class="flex h-16 items-center justify-between border-b bg-white px-4">
				<div class="text-lg font-semibold">{{ dashboard.doc.title }}</div>
				<div class="flex gap-2">
					<Button
						variant="outline"
						icon-left="refresh-ccw"
						@click="() => dashboard.refresh()"
					>
						Refresh
					</Button>
					<Button
						variant="outline"
						icon-left="plus"
						@click="showChartSelectorDialog = true"
					>
						Chart
					</Button>
					<Button
						variant="outline"
						icon-left="plus"
						@click="showFilterSelectorDialog = true"
					>
						Filter
					</Button>
				</div>
			</div>
			<div class="flex-1 overflow-y-auto p-3">
				<VueGridLayout
					v-if="dashboard.doc.items.length > 0"
					class="h-fit w-full"
					:class="[false ? 'mb-[20rem] ' : '']"
					:cols="20"
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
						<div class="relative h-full w-full p-1.5">
							<DashboardItem :index="index" :item="dashboard.doc.items[index]" />
							<DashboardItemActions
								class="absolute right-0 top-1 -mr-7"
								v-if="dashboard.isActiveItem(index)"
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

	<FilterSelectorDialog
		v-model="showFilterSelectorDialog"
		:charts="props.charts"
		:queries="props.queries"
		@select="dashboard.addFilter($event)"
	/>
</template>
