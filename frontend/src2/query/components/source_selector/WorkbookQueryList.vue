<script setup lang="ts">
import { ListView } from 'frappe-ui'
import { CheckIcon, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { computed, h, inject, ref } from 'vue'
import { QueryTableArgs } from '../../../types/query.types'
import { Workbook, workbookKey } from '../../../workbook/workbook'
import { Query } from '../../query'

const workbook = inject<Workbook>(workbookKey)!
const currentQuery = inject<Query>('query')!
const selectedQuery = defineModel<QueryTableArgs>('selectedQuery')

const querySearchTxt = ref(selectedQuery.value?.query_name || '')
const linkedQueries = workbook.getLinkedQueries(currentQuery.doc.name)
const validQueries = workbook.doc.queries.filter(
	(q) => q.name !== currentQuery.doc.name && !linkedQueries.includes(q.name)
)
const queries = computed(() => {
	if (!querySearchTxt.value) {
		return validQueries
	}
	return validQueries.filter((query) => {
		return (
			query.name.includes(querySearchTxt.value) || query.title?.includes(querySearchTxt.value)
		)
	})
})

const listColumns = [
	{
		label: 'Title',
		key: 'title',
		width: 2,
		prefix: () => h(Table2Icon, { class: 'h-4 w-4 text-gray-600' }),
	},
	{
		label: 'Source',
		key: 'source',
		width: 1,
		getLabel: (props: any) => props.row.operations?.[0]?.table?.table_name,
	},
	{
		label: '',
		key: 'selected',
		width: '40px',
		getLabel: () => '',
		prefix: (props: any) => {
			if (props.row.name === selectedQuery.value?.query_name) {
				return h(CheckIcon, { class: 'h-4 w-4' })
			}
		},
	},
]
</script>

<template>
	<div class="flex h-full flex-col gap-2 overflow-auto p-8 px-10">
		<h1 class="text-xl font-semibold">Queries</h1>
		<div class="flex justify-between overflow-visible py-1">
			<div class="flex gap-2">
				<FormControl
					placeholder="Search by Title"
					v-model="querySearchTxt"
					autocomplete="off"
				>
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-gray-500" />
					</template>
				</FormControl>
			</div>
		</div>
		<ListView
			v-if="queries.length"
			class="h-full"
			:columns="listColumns"
			:rows="queries"
			:row-key="'name'"
			:options="{
				selectable: false,
				showTooltip: false,
				onRowClick: (row: any) => {
					selectedQuery = {
						type: 'query',
						workbook: workbook.doc.name,
						query_name: row.name,
					}
				},
				emptyState: {
					title: 'No Queries Found'
				},
			}"
		>
		</ListView>
	</div>
</template>
