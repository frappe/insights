<script setup lang="ts">
import { computed, inject } from 'vue'
import { Chart, getCachedChart } from '../charts/chart'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import ColumnFilter from '../query/components/ColumnFilter.vue'
import DataTypeIcon from '../query/components/DataTypeIcon.vue'
import { Query, getCachedQuery } from '../query/query'
import {
	WorkbookDashboardChart,
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
} from '../workbook/workbook'
import { Dashboard } from './dashboard'

const props = defineProps<{
	index: number
	item: WorkbookDashboardItem
}>()

const dashboard = inject('dashboard') as Dashboard

const chart = computed(() => {
	if (props.item.type != 'chart') return null
	const item = props.item as WorkbookDashboardChart
	return getCachedChart(item.chart) as Chart
})
const filter = computed(() => {
	if (props.item.type != 'filter') return null
	return props.item as WorkbookDashboardFilter
})
function getDistinctColumnValues(searchTxt: string) {
	if (!filter.value) return
	const query = getCachedQuery(filter.value.column.query) as Query
	return query.getDistinctColumnValues(filter.value.column.name, searchTxt)
}
function handleApplyFilter(operator: FilterOperator, value: FilterValue) {
	if (!filter.value) return
	dashboard.applyFilter(filter.value.column, operator, value)
}
</script>

<template>
	<div
		class="flex h-full w-full items-center rounded"
		:class="[
			props.item.type == 'chart' ? ' bg-white shadow' : '',
			dashboard.editing && dashboard.isActiveItem(index) ? 'outline outline-gray-700' : '',
		]"
		@click="dashboard.setActiveItem(index)"
	>
		<div class="h-full w-full" :class="dashboard.editing ? 'pointer-events-none' : ''">
			<ChartRenderer v-if="chart" :chart="chart" />

			<div v-if="filter" class="flex-1">
				<ColumnFilter
					placement="bottom-start"
					:column="filter.column"
					:valuesProvider="getDistinctColumnValues"
					@filter="handleApplyFilter"
				>
					<template #target="{ togglePopover, isOpen }">
						<div class="relative flex-1">
							<Button
								variant="outline"
								@click="togglePopover"
								class="h-8 w-full !justify-start border-0 shadow"
							>
								<template #prefix>
									<DataTypeIcon :column-type="filter.column.type" />
								</template>
								{{ filter.column.name }}
							</Button>
							<div class="absolute top-0 right-0.5 flex h-full items-center">
								<Button
									variant="ghost"
									:disabled="!isOpen"
									:icon="isOpen ? 'x' : 'chevron-down'"
									@click=""
								/>
							</div>
						</div>
					</template>
				</ColumnFilter>
			</div>
		</div>
	</div>
</template>
