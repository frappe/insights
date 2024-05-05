<script setup lang="ts">
import { Analysis, analysisKey } from '@/analysis/useAnalysis'
import FiltersSelector from '@/query/next/FiltersSelector.vue'
import { ListFilter, RefreshCcw } from 'lucide-vue-next'
import { inject } from 'vue'
import { useAnalysisChart } from '../useAnalysisChart'
import { useAnalysisDashboard } from '../useAnalysisDashboard'
import ChartRenderer from './ChartRenderer.vue'

const analysis = inject(analysisKey) as Analysis
if (!analysis.dashboardName) {
	throw new Error('Dashboard name is required')
}
const query = analysis.model.queries[0]
const dashboard = useAnalysisDashboard(analysis.dashboardName, analysis)
analysis.charts.forEach((chart) => {
	dashboard.addChart(useAnalysisChart(chart.name, analysis.model))
})
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="relative flex w-[16rem] flex-shrink-0 flex-col overflow-y-auto bg-white"></div>
		<div class="relative flex h-full w-full flex-col overflow-hidden">
			<div class="flex h-16 items-center justify-between border-b bg-white px-4">
				<div class="text-lg font-semibold">Dashboard</div>
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
									:columnOptions="query.result.columnOptions"
									:columnValuesProvider="query.getDistinctColumnValues"
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
						<ChartRenderer :chart="chart" />
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
