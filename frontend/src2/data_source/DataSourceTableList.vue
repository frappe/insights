<script setup lang="tsx">
import { watchDebounced } from '@vueuse/core'
import { Breadcrumbs, ListView } from 'frappe-ui'
import { MoreHorizontal, RefreshCcw, SearchIcon } from 'lucide-vue-next'
import { h, ref, watchEffect } from 'vue'
import useDataSourceStore from './data_source'
import useTableStore, { DataSourceTable } from './tables'

const props = defineProps<{ name: string }>()

const dataSource = useDataSourceStore().getSource(props.name)
const tableStore = useTableStore()

const searchQuery = ref('')
const filteredTables = ref<DataSourceTable[]>()
watchDebounced(searchQuery, () => updateTablesList(), { debounce: 300, immediate: true })

function updateTablesList() {
	tableStore.getTables(props.name, searchQuery.value).then((tables) => {
		filteredTables.value = tables
	})
}

const listOptions = ref({
	columns: [
		{
			label: 'Table Name',
			key: 'table_name',
		},
	],
	rows: filteredTables,
	rowKey: 'table_name',
	options: {
		showTooltip: false,
		getRowRoute: (table: DataSourceTable) => ({
			path: `/data-source/${props.name}/${table.table_name}`,
		}),
		emptyState: {
			title: 'No Tables Found',
			description: 'No tables found for the selected data source.',
			button: {
				label: 'Refresh',
				iconLeft: 'refresh-ccw',
				variant: 'outline',
				loading: tableStore.updatingDataSourceTables,
				onClick: () =>
					tableStore.updateDataSourceTables(props.name).then(() => updateTablesList()),
			},
		},
	},
})

const dataSourceStore = useDataSourceStore()
watchEffect(() => {
	const ds = dataSourceStore.getSource(props.name)
	document.title = `Tables | ${props.name || ds?.title}`
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs
			:items="[
				{ label: 'Data Sources', route: '/data-source' },
				{ label: dataSource?.title || props.name, route: `/data-source/${props.name}` },
			]"
		/>
		<div class="flex items-center gap-2"></div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search by Title" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
			<Dropdown
				:options="[
					{
						label: 'Update Tables',
						onClick: () =>
							tableStore
								.updateDataSourceTables(props.name)
								.then(() => updateTablesList()),
						icon: () =>
							h(RefreshCcw, {
								class: 'h-4 w-4 text-gray-700',
								'stroke-width': '1.5',
							}),
					},
					dataSource?.is_frappe_db
						? {
								label: 'Update Table Links',
								onClick: () => tableStore.updateTableLinks(props.name),
								icon: () =>
									h(RefreshCcw, {
										class: 'h-4 w-4 text-gray-700',
										'stroke-width': '1.5',
									}),
						  }
						: null,
				]"
			>
				<Button>
					<template #icon>
						<MoreHorizontal class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Dropdown>
		</div>
		<ListView class="h-full" v-bind="listOptions"> </ListView>
	</div>
</template>
