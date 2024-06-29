<script setup lang="ts">
import { wheneverChanges } from '@/utils'
import { ListEmptyState, ListView } from 'frappe-ui'
import { Check, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { computed, h, ref } from 'vue'
import useTableStore from '../../data_source/tables'
import { SourceArgs } from '../../types/query.types'
import { table } from '../helpers'
import DataSourceSelector from './DataSourceSelector.vue'

const emit = defineEmits({
	select: (args: SourceArgs) => true,
})
const showDialog = defineModel()

const tableStore = useTableStore()

const dataSourceFilter = ref('')
const tableSearchQuery = ref('')
wheneverChanges(
	() => [tableSearchQuery.value, dataSourceFilter.value],
	() => tableStore.getTables(dataSourceFilter.value, tableSearchQuery.value),
	{ debounce: 300, immediate: true }
)

const listColumns = [
	{
		label: 'Table',
		key: 'table_name',
		width: 2,
		prefix: () => h(Table2Icon, { class: 'h-4 w-4 text-gray-600' }),
	},
	{
		label: 'Data Source',
		key: 'data_source',
		width: 1,
	},
	{
		label: '',
		key: 'selected',
		width: '40px',
		getLabel: () => '',
		prefix: ({ row }: any) => row.selected && h(Check, { class: 'h-4 w-4' }),
	},
]

const confirmDisabled = computed(() => {
	if (!tableStore.tables) return true
	return tableStore.tables.every((table: any) => !table.selected)
})
function onConfirm() {
	if (confirmDisabled.value) return
	const selectedTable = tableStore.tables.find((table: any) => table.selected)
	if (!selectedTable) return
	emit('select', {
		table: table(selectedTable.data_source, selectedTable.table_name),
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
			<div class="flex h-[20rem] flex-col gap-2 overflow-auto p-0.5">
				<div class="flex gap-2 overflow-visible py-1">
					<FormControl
						placeholder="Search by Title"
						v-model="tableSearchQuery"
						autocomplete="off"
					>
						<template #prefix>
							<SearchIcon class="h-4 w-4 text-gray-500" />
						</template>
					</FormControl>
					<DataSourceSelector v-model="dataSourceFilter"> </DataSourceSelector>
				</div>
				<ListView
					v-if="tableStore.tables.length"
					class="h-full"
					:columns="listColumns"
					:rows="tableStore.tables"
					:row-key="'name'"
					:options="{
						selectable: false,
						showTooltip: false,
						onRowClick: (row: any) => {
							tableStore.tables.forEach((row: any) => (row.selected = 0))
							row.selected = 1
						},
						emptyState: {
							title: 'No Tables Found',
							description: 'Sync tables from your data source to get started',
						},
					}"
				>
					<ListEmptyState v-if="tableStore.loading">
						<LoadingIndicator class="h-6 w-6 text-gray-600" />
					</ListEmptyState>
				</ListView>
			</div>
		</template>
	</Dialog>
</template>
