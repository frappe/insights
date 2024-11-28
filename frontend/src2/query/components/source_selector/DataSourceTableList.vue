<script setup lang="ts">
import { ListView } from 'frappe-ui'
import { CheckIcon, RefreshCcw, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { computed, h, ref } from 'vue'
import useTableStore from '../../../data_source/tables'
import { wheneverChanges } from '../../../helpers'
import { TableArgs } from '../../../types/query.types'
import useDataSourceStore from '../../../data_source/data_source'

const props = defineProps<{ data_source: string }>()
const dataSourceStore = useDataSourceStore()
const dataSource = computed(() => dataSourceStore.getSource(props.data_source))

const tableStore = useTableStore()

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

const emptyState = computed(() => {
	if (tableStore.updatingDataSourceTables) {
		return {
			title: 'Refreshing Tables',
			description: 'Please wait while we refresh the tables from your data source',
		}
	}

	return {
		title: 'No Tables Found',
		description: 'Sync tables from your data source to get started',
		button: {
			variant: 'outline',
			label: 'Refresh Tables',
			onClick: () => tableStore.updateDataSourceTables(props.data_source),
		},
	}
})
</script>

<template>
	<div class="flex h-full flex-col gap-2 overflow-auto p-8 px-10">
		<h1 class="text-xl font-semibold">{{ dataSource?.title }}</h1>
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
			:rows="tableStore.tables[props.data_source] || []"
			:row-key="'name'"
			:options="{
				selectable: false,
				showTooltip: false,
				onRowClick: (row: any) => (selectedTable = row),
				emptyState: emptyState,
			}"
		>
		</ListView>
	</div>
</template>
