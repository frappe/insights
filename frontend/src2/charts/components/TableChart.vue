<script setup lang="ts">
import { ChartContainer } from 'frappe-ui/charts'
import DataTable from '../../components/DataTable.vue'
import type { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import type { TableCellEvent, TableChartProps } from '../adapter/table'

// The grid a Table Chart draws instead of a plot. It is a filler like any
// other: the title and every state around it are `ChartBody`'s, and the card is
// whoever framed it, so nothing here draws a surface of its own. It holds the
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
		<!-- The grid runs to the card's own edges, so its first and last columns
		     end on the card border instead of floating 16px inside it. Nothing
		     else in the card moves: the title keeps the card's padding, and the
		     card clips the overhang. The frame names its own padding in
		     `--chart-card-inset`, and a table with no card around it bleeds by
		     nothing.
		     The last column drops its own right border once it is flush: the
		     card's border is already that line, and both drawn is a double rule.
		     A box of its own, not classes on the table: DataTable renders a
		     fragment — the grid, the empty state and the loading veil are
		     siblings — so an inherited class would reach none of them. `relative`
		     is for the veil, which is absolute and should cover the bled width. -->
		<div
			class="relative mt-1 h-full [&_tr>*:last-child]:border-r-0 [margin-inline:calc(var(--chart-card-inset,0px)*-1)] [width:calc(100%_+_2_*_var(--chart-card-inset,0px))]"
		>
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
				:cell-link="props.cellLink"
				:replace-nulls-with-zeros="true"
			/>
		</div>
	</ChartContainer>
</template>
