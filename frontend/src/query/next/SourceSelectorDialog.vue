<script setup lang="ts">
import dayjs from '@/utils/dayjs'
import { createListResource, ListView } from 'frappe-ui'
import { Check, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { computed, h, ref, watch } from 'vue'

const emit = defineEmits(['select'])
const showDialog = defineModel()

const defaultFilters = { hidden: 0, is_query_based: 0 }
const tables = createListResource({
	doctype: 'Insights Table',
	cache: 'allTables',
	fields: ['name', 'table', 'label', 'data_source', 'creation', 'modified'],
	filters: defaultFilters,
	auto: true,
	pageLength: 50,
	orderBy: 'creation desc',
	transform(data: any) {
		return data.map((table: any) => {
			return {
				...table,
				created_from_now: dayjs(table.creation).fromNow(),
			}
		})
	},
})

const tableSearchQuery = ref('')
watch(tableSearchQuery, (query: any) => {
	const filters: any = { ...defaultFilters }
	if (query) filters.label = ['like', `%${query}%`]
	tables.update({ filters })
	tables.reload()
})

const filteredTables = computed(() => {
	if (!tables.data) return []
	if (!tableSearchQuery.value) return tables.data
	return tables.data.filter((table: any) => {
		return table.label.toLowerCase().includes(tableSearchQuery.value.toLowerCase())
	})
})

const listColumns = [
	{
		label: 'Table',
		key: 'label',
		width: 2,
		prefix: () => h(Table2Icon, { class: 'h-4 w-4 text-gray-600' }),
	},
	{ label: 'Data Source', key: 'data_source', width: 1 },
	{ label: 'Created', key: 'created_from_now', width: 1 },
	{
		label: '',
		key: 'selected',
		width: '40px',
		getLabel: () => '',
		prefix: ({ row }: any) => row.selected && h(Check, { class: 'h-4 w-4' }),
	},
]

const confirmDisabled = computed(() => {
	return filteredTables.value.every((table: any) => !table.selected)
})
function onConfirm() {
	if (confirmDisabled.value) return
	const selectedTable = filteredTables.value.find((table: any) => table.selected)
	emit('select', {
		table: selectedTable.table,
		data_source: selectedTable.data_source,
	})
	showDialog.value = false
}
</script>

<template>
	<Dialog
		v-model="showDialog"
		:options="{
			title: 'Pick starting data',
			size: '4xl',
			actions: [
				{
					label: 'Confirm',
					variant: 'solid',
					disabled: confirmDisabled,
					onClick: onConfirm,
				},
			],
		}"
	>
		<template #body-content>
			<div class="mb-4 flex h-[20rem] flex-col gap-2 overflow-auto p-0.5">
				<div class="flex gap-2 overflow-visible py-1">
					<FormControl
						placeholder="Search by Title"
						v-model="tableSearchQuery"
						:debounce="300"
					>
						<template #prefix>
							<SearchIcon class="h-4 w-4 text-gray-500" />
						</template>
					</FormControl>
				</div>
				<ListView
					:columns="listColumns"
					:rows="filteredTables"
					:row-key="'name'"
					:options="{
						selectable: false,
						showTooltip: false,
						onRowClick: (row: any) => {
							filteredTables.forEach((row: any) => (row.selected = 0))
							row.selected = 1
						},
						emptyState: {
							title: 'No Tables Found',
							description: 'Sync tables from your data source to get started',
						},
					}"
				>
				</ListView>
			</div>
		</template>
	</Dialog>
</template>
