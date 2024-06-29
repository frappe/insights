<script setup lang="ts">
import { wheneverChanges } from '@/utils'
import { ListEmptyState, ListView } from 'frappe-ui'
import { Check, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { computed, h, ref } from 'vue'
import useTableStore from '../../data_source/tables'
import { SourceArgs, TableArgs } from '../../types/query.types'
import { table } from '../helpers'
import DataSourceSelector from './DataSourceSelector.vue'

const emit = defineEmits({ select: (source: SourceArgs) => true })
const props = defineProps<{ source?: SourceArgs }>()
const showDialog = defineModel()

const selectedTable = ref<TableArgs>(
	props.source
		? { ...props.source.table }
		: {
				data_source: '',
				table_name: '',
		  }
)

const tableStore = useTableStore()

const dataSourceFilter = ref('')
const tableSearchQuery = ref(props.source ? props.source.table.table_name : '')
wheneverChanges(
	() => [tableSearchQuery.value, dataSourceFilter.value],
	() => tableStore.getTables(dataSourceFilter.value, tableSearchQuery.value),
	{ debounce: 300, immediate: true }
)

const confirmDisabled = computed(() => {
	if (!tableStore.tables) return true
	return !selectedTable.value.table_name
})

function onConfirm() {
	if (confirmDisabled.value) return
	emit('select', { table: table(selectedTable.value) })
	showDialog.value = false
}

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
			props.row.table_name === selectedTable.value.table_name &&
			h(Check, { class: 'h-4 w-4' }),
	},
]
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
						onRowClick: (row: any) => (selectedTable = row),
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
