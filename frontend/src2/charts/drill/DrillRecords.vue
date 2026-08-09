<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { ExternalLink } from 'lucide-vue-next'
import { computed } from 'vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { EMPTY_RESULT, formatResultRows, rawRowOf } from '../../query/helpers'
import type { ResultTable } from '../../query/result_table'
import { __ } from '../../translation'
import type { QueryResultRow } from '../../types/query.types'
import { drillGranularity, type DrillLevelData } from './drill_stack'

// The floor of the ladder: the rows behind the segment, every column the query
// selects and no more. What the author chose to publish is the query itself, so
// there is no column picking here, no group-by, and no way further down — the
// crumbs above are the way back up.
const props = defineProps<{ data: DrillLevelData }>()

// The rows arrive whole, in one response, so there is one page and none of the
// authoring half. `ResultTable` is written for exactly that: what is not handed
// over is not drawn.
const table = computed<ResultTable>(() => {
	const result = {
		...EMPTY_RESULT,
		columns: props.data.columns,
		rows: props.data.rows,
	}
	return {
		ready: true,
		executing: false,
		result: {
			...result,
			formattedRows: formatResultRows(result, drillGranularity(props.data.columns)),
			totalRowCount: props.data.total_row_count ?? props.data.rows.length,
		},
	}
})

// Whether a row names a desk document is the server's answer, carried on the
// response. Nothing here guesses a doctype from a column name: a miss shows no
// control rather than a control that lands on the wrong record.
const link = computed(() => props.data.record_link)

// The table draws the formatted rows, so the crossing back happens here — a
// document is named by what the query returned, not by what was printed.
function openRecord(formattedRow: QueryResultRow) {
	const row = rawRowOf(table.value.result, formattedRow)
	const name = row?.[link.value!.column]
	if (name === null || name === undefined || name === '') return
	const doctype = link.value!.doctype.toLowerCase().replace(/ /g, '-')
	// a new tab, so the drill stack behind it survives the jump
	window.open(`/app/${doctype}/${encodeURIComponent(String(name))}`, '_blank')
}
</script>

<template>
	<QueryDataTable :query="table">
		<template v-if="link" #row-action="{ row }">
			<Tooltip :text="__('Open record')" :hover-delay="0.5">
				<Button variant="ghost" @click="openRecord(row)">
					<template #icon>
						<ExternalLink class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
			</Tooltip>
		</template>
	</QueryDataTable>
</template>
