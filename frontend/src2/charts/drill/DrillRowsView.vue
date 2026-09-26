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

const props = defineProps<{
	answer: DrillLevelData
	/** the levels that led here, sent to the server again on every request */
	levels: DrillLevel[]
	subject: DrillSubject
	findTarget?: HTMLElement | null
}>()

const rows = makeDrillRows(props.answer, props.subject.rows!(props.levels))
defineExpose({ rows })

// The server says which columns name a desk document, on every answer for this
// level. Nothing here guesses a doctype from a column name: a missed column gets
// no link, not a link to the wrong document.
const links = computed(() => rows.recordLinks)

// A filter can name only the columns in the answer, and the server checks each
// filter against the same columns.
const columns = computed(() => rows.result.columns || [])
const filters = computed<Filter[]>({
	get: () => rows.filters,
	set: (own) => rows.setFilters(own),
})

function recordLink(column: QueryResultColumn, row: QueryResultRow) {
	const doctype = links.value?.[column.name]
	return doctype ? recordUrl(doctype, row[column.name]) : undefined
}
</script>

<template>
	<div class="flex h-full w-full overflow-hidden">
		<ResultPane :query="rows" :find-target="props.findTarget">
			<template #grid="{ rows: page, currentPage, pageSize }">
				<!-- no drill from here: the stack led the reader to these rows, and a
				     drill started inside it would nest a second stack -->
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

		<!-- Beside the find, in the dialog's row of level actions, as in the
		     builder's rows pane. It comes after the pane so it renders after the
		     find, which is teleported to the same target: filter narrows the
		     rows, find searches the result. -->
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
