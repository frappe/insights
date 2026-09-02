<script setup lang="ts">
import { computed } from 'vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { EMPTY_RESULT, formatResultRows } from '../../query/helpers'
import type { ResultTable } from '../../query/result_table'
import type { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { recordUrl } from '../record_link'
import { recordDateGranularity, type DrillLevelData } from './drill_stack'

// The floor of the stack: the rows behind the segment, every column the query
// selects and no more. What the author chose to publish is the query itself, so
// there is no column picking here, no group-by, and no way further down — the
// crumbs above are the way back up.
const props = defineProps<{ answer: DrillLevelData }>()

// The rows arrive whole, in one response, so there is one page and none of the
// authoring half. `ResultTable` is written for exactly that: what is not handed
// over is not drawn.
const table = computed<ResultTable>(() => {
	const result = {
		...EMPTY_RESULT,
		columns: props.answer.columns,
		rows: props.answer.rows,
	}
	return {
		ready: true,
		executing: false,
		result: {
			...result,
			formattedRows: formatResultRows(result, recordDateGranularity(props.answer.columns)),
			totalRowCount: props.answer.total_row_count ?? props.answer.rows.length,
		},
	}
})

// Which columns name a desk document is the server's answer, carried on the
// response. Nothing here guesses a doctype from a column name: a miss shows no
// control rather than a control that lands on the wrong record.
const links = computed(() => props.answer.record_links)

// The value is the control: a column that names a document links to its form,
// and every other cell stays a value. A cell naming nothing gets no link.
function recordLink(column: QueryResultColumn, row: QueryResultRow) {
	const doctype = links.value?.[column.name]
	return doctype ? recordUrl(doctype, row[column.name]) : undefined
}
</script>

<template>
	<!-- The grid runs to the card's own edges, the way a Table Chart's does, so
	     its first and last columns end on the card edge instead of floating 16px
	     inside it. `-mx-4` is the card's horizontal padding, which is the only
	     measurement this bleed depends on. The last column drops its own right
	     border once it is flush: the card's edge is already that line.
	     A box of its own, not classes on the table: DataTable renders a fragment,
	     so an inherited class would reach none of its parts. -->
	<div class="relative -mx-4 h-full w-[calc(100%_+_2rem)] [&_tr>*:last-child]:border-r-0">
		<QueryDataTable :query="table" :get-cell-link="links ? recordLink : undefined" />
	</div>
</template>
