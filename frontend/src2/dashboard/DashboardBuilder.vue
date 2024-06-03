<script setup lang="ts">
import FiltersSelector from '../query/components/FiltersSelector.vue'
import { ListFilter, RefreshCcw } from 'lucide-vue-next'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import useDashboard from './dashboard'
import useChart from '../charts/chart'

const props = defineProps<{ dashboard: WorkbookDashboard }>()
const dashboard = useDashboard(props.dashboard)
dashboard.doc.items = [
	{
		type: 'chart',
		chart: 'test',
		layout: {
			x: 0,
			y: 0,
			w: 6,
			h: 6,
		},
	},
]
async function valuesProvider(column_name: string, searchTxt?: string) {
	return []
}
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div class="flex h-16 items-center justify-between border-b bg-white px-4">
				<div class="text-lg font-semibold">{{ dashboard.doc.name }}</div>
				<div class="flex gap-2">
					<Button @click="dashboard.refresh">
						<template #prefix>
							<RefreshCcw class="h-4 w-4" :stroke-width="1.5" />
						</template>
						Refresh
					</Button>
					<Popover>
						<template #target="{ togglePopover }">
							<Button @click="togglePopover">
								<template #prefix>
									<ListFilter class="h-4 w-4" :stroke-width="1.5" />
								</template>
								Filter
								<template #suffix>
									<template v-if="dashboard.filters.length">
										<div
											class="flex h-4 w-4 items-center justify-center rounded bg-gray-800 text-xs font-semibold text-white"
										>
											{{ dashboard.filters.length }}
										</div>
									</template>
								</template>
							</Button>
						</template>
						<template #body-main="{ close }">
							<div class="w-[40rem] overflow-hidden rounded-lg">
								<FiltersSelector
									:filters="dashboard.filters"
									:columnOptions="[]"
									:columnValuesProvider="valuesProvider"
									@select="dashboard.setFilters"
									@close="close"
								/>
							</div>
						</template>
					</Popover>
				</div>
			</div>
			<div class="flex-1 overflow-y-auto">
				<div class="grid grid-cols-1 gap-4 p-4">
					<div
						v-for="(chart, idx) in dashboard.charts"
						:key="idx"
						class="max-h-[40rem] overflow-hidden rounded-lg border bg-white shadow-sm"
					>
						<ChartRenderer :chart="useChart(chart)" />
					</div>
				</div>
			</div>
		</div>
		<div class="relative flex w-[16rem] flex-shrink-0 flex-col overflow-y-auto bg-white"></div>
	</div>
</template>
