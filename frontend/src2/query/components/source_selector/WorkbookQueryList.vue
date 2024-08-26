<script setup lang="ts">
import { ListView } from 'frappe-ui'
import { CheckIcon, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { computed, h, inject, ref, watchEffect } from 'vue'
import { WorkbookQuery } from '../../../types/workbook.types'
import { Workbook, workbookKey } from '../../../workbook/workbook'
import { Query } from '../../query'

const workbook = inject<Workbook>(workbookKey)!
const currentQuery = inject<Query>('query')!
const selectedQuery = defineModel<string>('selectedQuery')

const querySearchTxt = ref(selectedQuery.value || '')
const queries = computed(() => {
	const _queriesExceptCurrent = workbook.doc.queries.filter(
		(query) => query.name !== currentQuery.doc.name
	)
	if (!querySearchTxt.value) {
		return _queriesExceptCurrent
	}
	return _queriesExceptCurrent.filter((query) => {
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
		prefix: (props: any) =>
			props.row.name === selectedQuery.value && h(CheckIcon, { class: 'h-4 w-4' }),
	},
]
</script>

<template>
	<div class="flex h-full flex-col gap-2 overflow-auto p-0.5">
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
				onRowClick: (row: any) => (selectedQuery = row.name),
				emptyState: {
					title: 'No Queries Found'
				},
			}"
		>
		</ListView>
	</div>
</template>
