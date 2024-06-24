<script setup lang="ts">
import { computed, inject } from 'vue'
import { Chart, getCachedChart } from '../charts/chart'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import ColumnFilter from '../query/components/ColumnFilter.vue'
import DataTypeIcon from '../query/components/DataTypeIcon.vue'
import { column } from '../query/helpers'
import { Query, getCachedQuery } from '../query/query'
import { FilterOperator, FilterValue } from '../types/query.types'
import {
	WorkbookDashboardChart,
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
} from '../types/workbook.types'
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
	dashboard.applyFilter(filter.value.column.query, {
		column: column(filter.value.column.name),
		operator,
		value,
	})
}
</script>

<template>
	<div
		class="flex h-full w-full items-center rounded"
		:class="[
			dashboard.editing && dashboard.isActiveItem(index) ? 'outline outline-gray-700' : '',
		]"
		@click="dashboard.setActiveItem(index)"
	>
		<ChartRenderer
			v-if="chart"
			:chart="chart"
			:class="dashboard.editing ? 'pointer-events-none' : ''"
		/>

		<div v-if="filter" class="flex-1" :class="dashboard.editing ? 'pointer-events-none' : ''">
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
</template>
