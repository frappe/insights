<script setup lang="ts">
import { createListResource, createResource, ListView } from 'frappe-ui'
import { Check, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { computed, h, ref, watch } from 'vue'
import dayjs from '../../helpers/dayjs'
import DataSourceSelector from './DataSourceSelector.vue'

const emit = defineEmits({
	select: (args: { table: string; data_source: string }) => true,
})
const showDialog = defineModel()

const tables = createResource({
	url: 'insights.insights.doctype.insights_data_source.insights_data_source.get_data_source_tables',
	cache: 'all_tables',
	auto: true,
	initialData: [],
})

const tableSearchQuery = ref('')
watch(tableSearchQuery, (query: any, old_query: any) => {
	if (query === old_query) return
	tables.submit({
		data_source: dataSourceFilter.value,
		table_name_like: query,
	})
})

const dataSourceFilter = ref('')
watch(dataSourceFilter, (data_source: any) => {
	tables.submit({
		data_source: data_source,
		table_name_like: tableSearchQuery.value,
	})
})

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
	if (!tables.data) return true
	return tables.data.every((table: any) => !table.selected)
})
function onConfirm() {
	if (confirmDisabled.value) return
	const selectedTable = tables.data.find((table: any) => table.selected)
	emit('select', {
		table: selectedTable.table_name,
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
					<DataSourceSelector v-model="dataSourceFilter"> </DataSourceSelector>
				</div>
				<ListView
					:columns="listColumns"
					:rows="tables.data"
					:row-key="'name'"
					:options="{
						selectable: false,
						showTooltip: false,
						onRowClick: (row: any) => {
							tables.data.forEach((row: any) => (row.selected = 0))
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
