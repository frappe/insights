<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue'
import { toFilterGroup, type Filter } from '../../components/filter_picker/filter_picker'
import FilterPicker from '../../components/filter_picker/FilterPicker.vue'
import ResultPane from '../../components/result_pane/ResultPane.vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import QueryOperations from '../../query/components/QueryOperations.vue'
import { filter_group } from '../../query/helpers'
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

// --- the reader's own filters over these rows -------------------------------
//
// Held here, so they last exactly as long as the level does: a new rows level
// mounts a new component, and closing the dialog unmounts this one. Nothing is
// carried back to the surface.
//
// Every column here is a plain column — these are the sliced source rows, not a
// summarize — so a number operator is a `WHERE` like any other.
const filters = ref<Filter[]>([])
const columns = computed(() => query.result.columns || [])

function valuesProvider(column: QueryResultColumn) {
	return (search: string) => query.getDistinctColumnValues(column.name, search)
}

// The surface's routed groups are the surface's: they are passed through
// untouched, and the reader's rules are one more group under this query's own
// name, which is the key the server matches these rows against. Should a group
// already stand under that name, both hold — `And`.
watch(filters, () => {
	const routed = props.adhocFilters || {}
	const routedGroup = routed[query.doc.name]
	const own = toFilterGroup(filters.value)
	query.adhocFilters = filters.value.length
		? {
				...routed,
				[query.doc.name]: routedGroup
					? filter_group({
							logical_operator: 'And',
							filters: [...routedGroup.filters, ...own.filters],
					  })
					: own,
		  }
		: { ...routed }
	// narrower rows are a different first page, and going to it runs the query
	query.goToPage(1)
})

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

			<!-- Beside the find, in the dialog's row of level actions. It is drawn
			     after the pane so that it lands after the find the pane teleports
			     into the same host: filter reads the rows, find reads the result. -->
			<Teleport v-if="props.findTarget" :to="props.findTarget">
				<FilterPicker
					v-model="filters"
					:columns="columns"
					:values-provider="valuesProvider"
				/>
			</Teleport>
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
