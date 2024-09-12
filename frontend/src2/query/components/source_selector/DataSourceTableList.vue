<script setup lang="ts">
import { ListEmptyState, ListView } from 'frappe-ui'
import { CheckIcon, RefreshCcw, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { h, ref } from 'vue'
import useTableStore from '../../../data_source/tables'
import { wheneverChanges } from '../../../helpers'
import { TableArgs } from '../../../types/query.types'

const props = defineProps<{ data_source: string }>()
const tableStore = useTableStore()
tableStore.getTables()

const selectedTable = defineModel<TableArgs>('selectedTable')

const tableSearchQuery = ref(selectedTable.value?.table_name || '')
wheneverChanges(
	() => [tableSearchQuery.value, props.data_source],
	() => tableStore.getTables(props.data_source, tableSearchQuery.value),
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
		prefix: (props: any) =>
			props.row.table_name === selectedTable.value?.table_name &&
			h(CheckIcon, { class: 'h-4 w-4' }),
	},
]
</script>

<template>
	<div class="flex h-full flex-col gap-2 overflow-auto p-0.5">
		<div class="flex justify-between overflow-visible py-1">
			<div class="flex gap-2">
				<FormControl
					placeholder="Search by Title"
					v-model="tableSearchQuery"
					autocomplete="off"
				>
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-gray-500" />
					</template>
				</FormControl>
			</div>
			<div>
				<Button
					variant="outline"
					label="Refresh Tables"
					:loading="tableStore.updatingDataSourceTables"
					@click="tableStore.updateDataSourceTables(props.data_source)"
				>
					<template #prefix>
						<RefreshCcw class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</div>
		</div>
		<ListView
			class="h-full"
			:columns="listColumns"
			:rows="tableStore.tables"
			:row-key="'name'"
			:options="{
				selectable: false,
				showTooltip: false,
				onRowClick: (row: any) => (selectedTable = row),
				emptyState: {
					title: 'No Tables Found',
					description: 'Sync tables from your data source to get started',
					button: {
						variant: 'outline',
						label: 'Refresh Tables',
						onClick: () => tableStore.updateDataSourceTables(props.data_source),
					},
				},
			}"
		>
		</ListView>
	</div>
</template>
