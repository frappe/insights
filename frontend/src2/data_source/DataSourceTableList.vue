<script setup lang="tsx">
import { watchDebounced } from '@vueuse/core'
import { Breadcrumbs, ListView } from 'frappe-ui'
import { MoreHorizontal, RefreshCcw, SearchIcon } from 'lucide-vue-next'
import { h, ref } from 'vue'
import useTableStore, { DataSourceTable } from './tables'

const props = defineProps<{ name: string }>()

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

document.title = `Tables | ${props.name}`
</script>

<template>
	<header class="mb-2 flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs
			:items="[
				{ label: 'Data Sources', route: '/data-source' },
				{ label: props.name, route: `/data-source/${props.name}` },
			]"
		/>
		<div class="flex items-center gap-2"></div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-2 overflow-auto px-4">
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
