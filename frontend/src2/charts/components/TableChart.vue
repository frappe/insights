<script setup lang="ts">
import { computed, watch } from 'vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { column } from '../../query/helpers'
import { TableChartConfig } from '../../types/chart.types'
import { DataFormat, SortDirection } from '../../types/query.types'
import { Query } from '../../query/query'
import { Chart } from '../chart'
import ChartTitle from './ChartTitle.vue'

const props = defineProps<{ chart: Chart }>()
defineEmits<{ drillDown: [query: Query] }>()
const tableConfig = computed(() => props.chart.doc.config as TableChartConfig)

// Maps a value column to its display format (e.g. percent) so the table can
// render a rate measure as `59%` instead of `0.59`.
const columnFormats = computed(() => {
	const formats: Record<string, DataFormat> = {}
	tableConfig.value.values?.forEach((measure) => {
		if (measure?.measure_name && measure.format) {
			formats[measure.measure_name] = measure.format
		}
	})
	return formats
})

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
	<div
		class="flex h-full w-full flex-col divide-y overflow-hidden rounded bg-surface-base border border-outline-gray-2"
	>
		<ChartTitle :title="props.chart.doc.title" />
		<QueryDataTable
			:query="props.chart.dataQuery"
			:show-filter-row="tableConfig.show_filter_row"
			:show-column-totals="tableConfig.show_column_totals"
			:show-row-totals="tableConfig.show_row_totals"
			:compact-numbers="tableConfig.compact_numbers"
			:enable-color-scale="tableConfig.enable_color_scale"
			:format-group="tableConfig.conditional_formatting"
			:enable-sort="true"
			:enable-drill-down="true"
			@drill-down="$emit('drillDown', $event)"
			:on-sort-change="onSortChange"
			:sticky-columns="tableConfig.sticky_columns"
			:column-widths="tableConfig.column_widths"
			:text-wrap="tableConfig.text_wrap"
			:column-formats="columnFormats"
			:replace-nulls-with-zeros="true"
		></QueryDataTable>
	</div>
</template>
