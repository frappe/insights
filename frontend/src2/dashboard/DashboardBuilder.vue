<script setup lang="ts">
import { Edit3, RefreshCcw } from 'lucide-vue-next'
import { computed, provide, ref } from 'vue'
import {
	WorkbookChart,
	WorkbookDashboard,
	WorkbookDashboardChart,
	WorkbookQuery,
} from '../workbook/workbook'
import ChartSelectorDialog from './ChartSelectorDialog.vue'
import useDashboard from './dashboard'
import DashboardFilterSelector from './DashboardFilterSelector.vue'
import DashboardItem from './DashboardItem.vue'
import DashboardItemActions from './DashboardItemActions.vue'
import VueGridLayout from './VueGridLayout.vue'

const props = defineProps<{
	dashboard: WorkbookDashboard
	charts: WorkbookChart[]
	queries: WorkbookQuery[]
}>()

const dashboard = useDashboard(props.dashboard)
provide('dashboard', dashboard)
dashboard.refresh()

const selectedCharts = computed(() => {
	return dashboard.doc.items.filter((item) => item.type == 'chart') as WorkbookDashboardChart[]
})

const showChartSelectorDialog = ref(false)
const showTextWidgetCreationDialog = ref(false)
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div class="flex items-center justify-between border-x bg-white py-3 px-4 shadow-sm">
				<div class="text-lg font-semibold">{{ dashboard.doc.title }}</div>
				<div class="flex gap-2">
					<DashboardFilterSelector
						v-if="!dashboard.editing"
						:queries="props.queries"
						:charts="props.charts"
					/>
					<Button
						v-if="!dashboard.editing"
						variant="outline"
						@click="() => dashboard.refresh()"
					>
						<template #icon>
							<RefreshCcw class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<Button
						v-if="!dashboard.editing"
						variant="outline"
						@click="dashboard.editing = true"
					>
						<template #icon>
							<Edit3 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<Button
						v-if="dashboard.editing"
						variant="outline"
						icon-left="check"
						@click="dashboard.editing = false"
					>
						Done
					</Button>
					<template v-if="dashboard.editing">
						<Button
							variant="outline"
							icon-left="plus"
							@click="showChartSelectorDialog = true"
						>
							Chart
						</Button>
					</template>
				</div>
			</div>
			<div class="flex-1 overflow-y-auto p-2">
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
						<div class="relative h-full w-full p-2">
							<DashboardItem :index="index" :item="dashboard.doc.items[index]" />
							<DashboardItemActions
								v-if="dashboard.editing && dashboard.isActiveItem(index)"
								class="absolute right-0 top-1.5 -mr-7"
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
