<script setup lang="ts">
import { ChartContainer } from 'frappe-ui/charts'
import { computed, inject, ref } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { findRows } from '../../components/result_pane/find'
import type { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import {
	cardFilterRules,
	tableCardFilterKey,
	tableFindKey,
	type TableCellEvent,
	type TableChartProps,
} from '../adapter/table'

// The grid a Table Chart draws instead of a plot. It is a filler like any
// other: the title and every state around it are `ChartBody`'s, and the card is
// whoever drew the chrome, so nothing here draws a surface of its own. It holds the
// table and reports a cell, and everything it puts on the table was decided in
// `adapter/table.ts`.
const props = defineProps<TableChartProps>()

const emit = defineEmits<{
	// eslint-disable-next-line no-unused-vars
	cellClick: [event: TableCellEvent]
}>()

// The find the host's box asks for. It runs over the rows this grid was handed
// — formatted, so a date matches the way it prints — and never over the ones
// the server kept back. A host with no find box provides none and every row
// stands.
const findText = inject(tableFindKey, ref(''))
const matches = computed(() => findRows(props.rows, findText.value))

// The filter row is the read's card filter, written one box per column: the
// read holds the text and takes the rules, and `ChartBody` hands it down on
// every surface. So the row is drawn wherever the config asks for it.
//
// A grid drawn outside a chart surface has no read behind it — a drill level
// that falls back to a table is drawn in the dialog, which is `ChartBody`'s
// sibling — so the holder is optional, and there the grid keeps its own text.
const cardFilter = inject(tableCardFilterKey, undefined)

function onFilterChange(text: Record<string, string>) {
	cardFilter?.apply(cardFilterRules(text, props.columns))
}

function onDrilldown(column: QueryResultColumn, row: QueryResultRow) {
	emit('cellClick', { column, row })
}
</script>

<template>
	<ChartContainer :title="props.title">
		<template v-if="$slots.actions" #actions>
			<slot name="actions" />
		</template>

		<!-- The grid runs to the card's own edges, so its first and last columns
		     end on the card border instead of floating 16px inside it. Nothing
		     else in the card moves: the title keeps the card's padding, and the
		     card clips the overhang. The chrome names its own padding in
		     `--chart-card-inset`, and a table with no card around it bleeds by
		     nothing.
		     The last column drops its own right border once it is flush: the
		     card's border is already that line, and both drawn is a double rule.
		     A box of its own, not classes on the table: DataTable renders a
		     fragment — the grid, the empty state and the loading veil are
		     siblings — so an inherited class would reach none of them.
		     The card draws the one loading veil, over the whole card: the grid
		     does not know a run is in flight and never veils itself. -->
		<div
			class="relative mt-1 h-full [&_tr>*:last-child]:border-r-0 [margin-inline:calc(var(--chart-card-inset,0px)*-1)] [width:calc(100%_+_2_*_var(--chart-card-inset,0px))]"
		>
			<DataTable
				:columns="props.columns"
				:rows="matches"
				:sort-order="props.sortOrder"
				:on-sort-change="props.onSortChange"
				:on-drilldown="props.drillable ? onDrilldown : undefined"
				:show-filter-row="props.showFilterRow"
				:filter-text="cardFilter?.text.value"
				:on-filter-change="cardFilter ? onFilterChange : undefined"
				:show-column-totals="props.showColumnTotals"
				:show-row-totals="props.showRowTotals"
				:enable-color-scale="props.enableColorScale"
				:format-group="props.formatGroup"
				:sticky-columns="props.stickyColumns"
				:column-widths="props.columnWidths"
				:text-wrap="props.textWrap"
				:column-formats="props.columnFormats"
				:number-format="props.numberFormat"
				:number-formats="props.numberFormats"
				:cell-link="props.cellLink"
				:replace-nulls-with-zeros="true"
			/>
		</div>
	</ChartContainer>
</template>
