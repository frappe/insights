<script setup lang="ts">
import { ref, watch } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../../query/query'
import { Operation, QueryResult, QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { getDrillDownQuery } from '../helpers'
import { column } from '../../query/helpers'

const props = defineProps<{
	chart: {
		operations: Operation[]
		use_live_connection?: boolean
		result: QueryResult
	}
	row: QueryResultRow
	column: QueryResultColumn
}>()

const showDrillDownResults = ref(false)
const drillDownQuery = ref<Query | null>(null)
const sortOrder = ref<Record<string, 'asc' | 'desc'>>({})

watch(
	() => props.row || props.column,
	() => {
		const query = getDrillDownQuery(
			props.chart.operations,
			props.chart.result,
			props.row,
			props.column,
			props.chart.use_live_connection
		)
		if (query) {
			showDrillDownResults.value = true
			drillDownQuery.value = query
			drillDownQuery.value.execute().then(() => {
				return drillDownQuery.value?.fetchResultCount()
			})
		}
	},
	{ immediate: true, deep: true }
)

function onSort(newSortOrder: Record<string, 'asc' | 'desc'>) {
	sortOrder.value = newSortOrder

	if (drillDownQuery.value) {
		Object.entries(newSortOrder).forEach(([columnName, direction]) => {
			drillDownQuery.value?.addOrderBy({
				column: column(columnName),
				direction,
			})
		})

		drillDownQuery.value
			.execute()
			.then(() => drillDownQuery.value?.fetchResultCount())
			.catch((error) => {
				console.error('Failed to sort and fetch row count:', error)
			})
	}
}

function loadAllRows() {
	if (drillDownQuery.value) {
		drillDownQuery.value.addLimit(drillDownQuery.value.result.totalRowCount)
		drillDownQuery.value
			.execute()
			.then(() => {
				return drillDownQuery.value?.fetchResultCount()
			})
			.catch((error) => {
				console.error('Failed to load all rows:', error)
			})
	}
}
</script>

<template>
	<Dialog
		v-model="showDrillDownResults"
		:options="{
			title: 'Drill Down Results',
			size: '5xl',
		}"
		@close="drillDownQuery = null"
	>
		<template #body-content>
			<div
				v-if="drillDownQuery"
				class="relative flex h-[35rem] w-full flex-1 flex-col overflow-hidden rounded border bg-white"
			>
				<DataTable
					:loading="drillDownQuery.executing"
					:columns="drillDownQuery.result.columns"
					:rows="drillDownQuery.result.rows"
					:enable-pagination="true"
					:show-column-totals="true"
					:show-filter-row="true"
					:sort-order="sortOrder"
					@sort="onSort"
					:on-export="drillDownQuery ? drillDownQuery.downloadResults : undefined"
				>
					<template #footer-left>
						<div class="flex items-center justify-between gap-4 p-1">
							<p class="tnum text-sm text-gray-600">
								Showing {{ drillDownQuery.result.rows.length }} of
								{{ drillDownQuery.result.totalRowCount }} rows
							</p>
							<Button
								v-if="
									drillDownQuery.result.rows.length <
									drillDownQuery.result.totalRowCount
								"
								:variant="'ghost'"
								theme="gray"
								size="sm"
								label="Load All Rows"
								@click="loadAllRows"
							>
							</Button>
						</div>
					</template>
				</DataTable>
			</div>
		</template>
	</Dialog>
</template>
