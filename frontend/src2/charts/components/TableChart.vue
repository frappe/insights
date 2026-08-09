<script setup lang="ts">
import { ChartContainer } from 'frappe-ui/charts'
import DataTable from '../../components/DataTable.vue'
import type { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import type { TableCellEvent, TableChartProps } from '../adapter/table'

// The grid a Table Chart draws instead of a plot. It is a filler like any
// other: the card, the title and every state around it are the chrome
// `ChartBody` draws, so nothing here draws a surface of its own. It holds the
// table and reports a cell, and everything it puts on the table was decided in
// `adapter/table.ts`.
const props = defineProps<TableChartProps>()

const emit = defineEmits<{
	// eslint-disable-next-line no-unused-vars
	cellClick: [event: TableCellEvent]
}>()

function onDrilldown(column: QueryResultColumn, row: QueryResultRow) {
	emit('cellClick', { column, row })
}
</script>

<template>
	<ChartContainer :title="props.title">
		<DataTable
			:columns="props.columns"
			:rows="props.rows"
			:loading="props.loading"
			:sort-order="props.sortOrder"
			:on-sort-change="props.onSortChange"
			:on-drilldown="props.drillable ? onDrilldown : undefined"
			:show-filter-row="props.showFilterRow"
			:show-column-totals="props.showColumnTotals"
			:show-row-totals="props.showRowTotals"
			:compact-numbers="props.compactNumbers"
			:enable-color-scale="props.enableColorScale"
			:format-group="props.formatGroup"
			:sticky-columns="props.stickyColumns"
			:column-widths="props.columnWidths"
			:text-wrap="props.textWrap"
			:column-formats="props.columnFormats"
			:replace-nulls-with-zeros="true"
		/>
	</ChartContainer>
</template>
