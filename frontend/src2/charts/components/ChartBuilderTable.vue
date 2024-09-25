<script setup lang="ts">
import { inject, ref } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../../query/query'
import { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { Chart } from '../chart'
import { getDrillDownQuery } from '../helpers'
import ChartBuilderTableColumn from './ChartBuilderTableColumn.vue'

const chart = inject('chart') as Chart

const showDrillDownResults = ref(false)
const drillDownQuery = ref<Query | null>(null)
function onCellClick(row: QueryResultRow, col: QueryResultColumn) {
	const query = getDrillDownQuery(chart, row, col)
	if (query) {
		drillDownQuery.value = query
		drillDownQuery.value.execute()
		showDrillDownResults.value = true
	}
}
</script>

<template>
	<div v-if="chart.doc.chart_type != 'Table'" class="flex h-[18rem] flex-col divide-y border">
		<DataTable
			class="bg-white"
			:columns="chart.dataQuery.result.columns"
			:rows="chart.dataQuery.result.formattedRows"
			@cell-dbl-click="onCellClick"
		>
			<template #column-header="{ column }">
				<ChartBuilderTableColumn :chart="chart" :column="column" />
			</template>
		</DataTable>

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
						:show-filter-row="true"
					>
						<template #footer>
							<div class="flex flex-shrink-0 items-center gap-3 border-t p-2">
								<p class="tnum text-sm text-gray-600">
									Showing {{ drillDownQuery.result.rows.length }} of
									{{ drillDownQuery.result.totalRowCount }} rows
								</p>
							</div>
						</template>
					</DataTable>
				</div>
			</template>
		</Dialog>
	</div>
</template>
