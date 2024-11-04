<script setup lang="ts">
import { ref, watch } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../../query/query'
import { Operation, QueryResult, QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { getDrillDownQuery } from '../helpers'

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
			drillDownQuery.value = query
			drillDownQuery.value.execute()
			showDrillDownResults.value = true
		}
	},
	{ immediate: true, deep: true }
)
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
					:show-column-totals="true"
					:show-filter-row="true"
				>
					<template #footer-left>
						<p class="tnum p-1 text-sm text-gray-600">
							Showing {{ drillDownQuery.result.rows.length }} of
							{{ drillDownQuery.result.totalRowCount }} rows
						</p>
					</template>
				</DataTable>
			</div>
		</template>
	</Dialog>
</template>
