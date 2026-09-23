<script setup lang="ts">
import { computed } from 'vue'
import type { Filter } from '../../components/filter_picker/filter_picker'
import FilterPicker from '../../components/filter_picker/FilterPicker.vue'
import ResultPane from '../../components/result_pane/ResultPane.vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import type { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { recordUrl } from '../record_link'
import type { DrillLevel, DrillLevelData, DrillSubject } from './drill_stack'
import { makeDrillRows } from './rows_view'

// The last level of the stack: the rows behind the segment, in the pane the
// query builder reads its results in.
//
// The pane and the grid are the same ones, so the sort, the find, the cursor
// and the export read and behave the same way. What differs is underneath: the
// query builder hands the pane a query it can run, and this hands it a source
// that asks the server.
const props = defineProps<{
	answer: DrillLevelData
	/** the walk that produced this level, which is what the server is re-asked with */
	levels: DrillLevel[]
	subject: DrillSubject
	/** where the dialog draws the find, above the pane and outside its border */
	findTarget?: HTMLElement | null
}>()

const rows = makeDrillRows(props.answer, props.subject.rows!(props.levels))
defineExpose({ rows })

// Which columns name a desk document is the server's answer, carried on every
// answer for this level. Nothing here guesses a doctype from a column name: a
// miss shows no control rather than a control that lands on the wrong document.
const links = computed(() => rows.recordLinks)

// The reader's own rules over these rows, written in the one filter picker. The
// columns a rule may name are the ones the answer drew, which is the surface the
// server checks each one against.
const columns = computed(() => rows.result.columns || [])
const filters = computed<Filter[]>({
	get: () => rows.filters,
	set: (own) => rows.setFilters(own),
})

// The value is the control: a column that names a document links to its form,
// and every other cell stays a value.
function recordLink(column: QueryResultColumn, row: QueryResultRow) {
	const doctype = links.value?.[column.name]
	return doctype ? recordUrl(doctype, row[column.name]) : undefined
}
</script>

<template>
	<div class="flex h-full w-full overflow-hidden">
		<ResultPane :query="rows" :find-target="props.findTarget">
			<template #grid="{ rows: page, currentPage, pageSize }">
				<!-- no drill from here: the stack is what got the reader to these
				     rows, and a second one started inside it recurses -->
				<QueryDataTable
					:query="rows"
					:rows="page"
					:current-page="currentPage"
					:page-size="pageSize"
					:enable-sort="true"
					:get-cell-link="links ? recordLink : undefined"
				/>
			</template>
		</ResultPane>

		<!-- Beside the find, in the dialog's row of level actions, the way the
		     builder's rows pane draws it. After the pane so that it lands after
		     the find teleported into the same host: filter reads the rows, find
		     reads the result. -->
		<Teleport v-if="props.findTarget" :to="props.findTarget">
			<FilterPicker
				v-model="filters"
				:columns="columns"
				:values-provider="rows.valuesProvider"
				:range-provider="rows.rangeProvider"
			/>
		</Teleport>
	</div>
</template>
