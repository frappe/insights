<script setup lang="ts">
import { provide, ref } from 'vue'
import ResultPane from '../../components/result_pane/ResultPane.vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import QueryOperations from '../../query/components/QueryOperations.vue'
import { makeAdhocQuery } from '../../query/query'
import { __ } from '../../translation'
import type { AdhocFilters, QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { recordUrl } from '../record_link'
import type { DrillLevelData } from './drill_stack'

// The last level of the stack: the rows behind the segment, as a query.
//
// The pipeline is the server's — the same slice it ran to answer the level — so
// nothing here derives anything. It is loaded into an ad-hoc query, which is a
// document nobody owns until someone saves it: closing the drill leaves the
// workbook exactly as it was.
//
// Running it here rather than reading the level's rows is what gives the reader
// sort, find, paging and export: they are the result pane's, and the pane needs
// a query behind it. The operations editor is the same query, shown on ask.
const props = defineProps<{
	/** an authoring level's answer, which is the only kind that carries a pipeline */
	answer: DrillLevelData
	title: string
	/** what the surface's own filters narrowed to, which the slice does not carry */
	adhocFilters?: AdhocFilters
	/** where the dialog draws the find, above the pane and outside its border */
	findTarget?: HTMLElement | null
}>()

const query = makeAdhocQuery()
query.doc.title = `${props.title} — ${__('Drill Down')}`
query.doc.use_live_connection = Boolean(props.answer.use_live_connection)
query.setOperations(props.answer.operations || [])
if (props.adhocFilters) query.adhocFilters = props.adhocFilters
// from here on it is the reader's query: every edit in the sidebar re-runs it
query.autoExecute = true
query.execute(true)

provide('query', query)

const editing = ref(false)

// Which columns name a desk document is the server's answer, carried on the
// level. Nothing here guesses a doctype from a column name: a miss shows no
// control rather than a control that lands on the wrong record.
const links = props.answer.record_links

// The value is the control: a column that names a document links to its form,
// and every other cell stays a value. A cell naming nothing gets no link.
function recordLink(column: QueryResultColumn, row: QueryResultRow) {
	const doctype = links?.[column.name]
	return doctype ? recordUrl(doctype, row[column.name]) : undefined
}

defineExpose({
	query,
	editing,
	toggleEditor: () => (editing.value = !editing.value),
})
</script>

<template>
	<div class="flex h-full w-full overflow-hidden">
		<div class="flex h-full min-w-0 flex-1 flex-col overflow-hidden">
			<!-- the reader's own query, run for them: no Execute, no query menu -->
			<ResultPane :query="query" :find-target="props.findTarget">
				<template #grid="{ rows, currentPage, pageSize }">
					<!-- no drill from here: the stack is what got the reader to these
					     rows, and a second one started inside it recurses -->
					<QueryDataTable
						:query="query"
						:rows="rows"
						:current-page="currentPage"
						:page-size="pageSize"
						:enable-sort="true"
						:get-cell-link="links ? recordLink : undefined"
					/>
				</template>
			</ResultPane>
		</div>
		<!-- the wrapper carries the row's gap, so closed it takes no space -->
		<div
			class="h-full flex-shrink-0 overflow-hidden transition-[width] duration-200 ease-out"
			:class="editing ? 'w-[17.75rem]' : 'w-0'"
		>
			<div
				class="relative ml-3 flex h-full w-[17rem] overflow-y-auto rounded-4 border border-outline-gray-2"
			>
				<QueryOperations />
			</div>
		</div>
	</div>
</template>
