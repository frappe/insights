<script setup lang="ts">
import { computed } from 'vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { column } from '../../query/helpers'
import { TableChartConfig } from '../../types/chart.types'
import { SortDirection } from '../../types/query.types'
import { Chart } from '../chart'
import ChartTitle from './ChartTitle.vue'

const props = defineProps<{ chart: Chart }>()

const tableConfig = computed(() => props.chart.doc.config as TableChartConfig)

function onSortChange(column_name: string, sort_order: SortDirection) {
	const existingOrder = props.chart.doc.config.order_by.find(
		(order) => order.column.column_name === column_name,
	)
	if (existingOrder) {
		if (sort_order) {
			existingOrder.direction = sort_order
		} else {
			props.chart.doc.config.order_by = props.chart.doc.config.order_by.filter(
				(order) => order.column.column_name !== column_name,
			)
		}
	} else {
		if (!sort_order) return
		props.chart.doc.config.order_by.push({
			column: column(column_name),
			direction: sort_order,
		})
	}
}
</script>

<template>
	<div class="flex h-full w-full flex-col divide-y overflow-hidden rounded bg-white shadow">
		<ChartTitle :title="props.chart.doc.title" />
		<QueryDataTable
			:query="props.chart.dataQuery"
			:show-filter-row="tableConfig.show_filter_row"
			:show-column-totals="tableConfig.show_column_totals"
			:show-row-totals="tableConfig.show_row_totals"
			:enable-color-scale="tableConfig.enable_color_scale"
			:enable-sort="true"
			:enable-drill-down="true"
			:on-sort-change="onSortChange"
			:sticky-columns="tableConfig.sticky_columns"
		></QueryDataTable>
	</div>
</template>
