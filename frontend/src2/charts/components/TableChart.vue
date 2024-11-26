<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { TableChartConfig } from '../../types/chart.types'
import { QueryResult, QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { WorkbookChart } from '../../types/workbook.types'
import { Chart } from '../chart'
import ChartTitle from './ChartTitle.vue'
import { column } from '../../query/helpers'
import DrillDown from './DrillDown.vue'

const props = defineProps<{
	title: string
	config: WorkbookChart['config']
	result: QueryResult
}>()

const chart = inject<Chart>('chart')!
const tableConfig = computed(() => props.config as TableChartConfig)

const sortOrder = computed(() => {
	const order_by = props.config.order_by
	const sort_order: Record<string, 'asc' | 'desc'> = {}
	order_by?.forEach((order) => {
		sort_order[order.column.column_name] = order.direction
	})
	return sort_order
})
function onSort(sort_order: Record<string, 'asc' | 'desc'>) {
	props.config.order_by = Object.keys(sort_order).map((column_name) => ({
		column: column(column_name),
		direction: sort_order[column_name],
	}))
}

const drillOn = ref<{ row: QueryResultRow; column: QueryResultColumn }>()
</script>

<template>
	<div class="flex h-full w-full flex-col divide-y overflow-hidden rounded bg-white shadow">
		<ChartTitle v-if="props.title" :title="props.title" />
		<DataTable
			:columns="props.result.columns"
			:rows="props.result.formattedRows"
			:show-filter-row="tableConfig.show_filter_row"
			:show-column-totals="tableConfig.show_column_totals"
			:show-row-totals="tableConfig.show_row_totals"
			:on-export="chart ? chart.dataQuery.downloadResults : undefined"
			:sort-order="sortOrder"
			@sort="onSort"
			@cell-dbl-click="(row, column) => (drillOn = { row, column })"
		>
		</DataTable>

		<DrillDown
			v-if="chart && drillOn"
			:chart="{
				operations: chart.doc.operations,
				use_live_connection: chart.baseQuery.doc.use_live_connection,
				result: chart.dataQuery.result,
			}"
			:row="drillOn.row"
			:column="drillOn.column"
		/>
	</div>
</template>
