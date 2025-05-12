<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { Breadcrumbs, ListView } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { ref, watchEffect } from 'vue'
import { getDatabaseLogo } from '../data_source/data_source'
import useDataStore, { DataStoreTable } from './data_store'
import ImportTableDialog from './ImportTableDialog.vue'
import session from '../session'

const dataStore = useDataStore()

const searchQuery = ref('')
const filteredTables = ref(dataStore.tables['__all'])
watchDebounced(
	searchQuery,
	() => {
		dataStore.getTables(undefined, searchQuery.value).then((tables) => {
			filteredTables.value = tables
		})
	},
	{ debounce: 300, immediate: true }
)

const showImportTableDialog = ref(false)

const listOptions = ref({
	columns: [
		{
			label: 'Table Name',
			key: 'table_name',
		},
		{
			label: 'Data Source',
			key: 'data_source',
			prefix: (props: any) => {
				const table = props.row as DataStoreTable
				return getDatabaseLogo(table.database_type, 'sm')
			},
		},
		{
			label: 'Last Synced',
			key: 'last_synced_from_now',
		},
	],
	rows: filteredTables,
	rowKey: 'name',
	options: {
		showTooltip: false,
		emptyState: {
			title: 'No Tables Stored',
			description: 'No tables found in the data store.',
			button: session.user.is_admin
				? {
						label: 'Import Table',
						iconLeft: 'plus',
						variant: 'solid',
						loading: false,
						onClick: () => (showImportTableDialog.value = true),
				  }
				: undefined,
		},
	},
})

watchEffect(() => {
	document.title = 'Data Store | Insights'
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: 'Data Store', route: '/data-store' }]" />
		<div class="flex items-center gap-2">
			<Button
				v-if="session.user.is_admin"
				label="Import Table"
				variant="solid"
				@click="showImportTableDialog = true"
			>
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>
		<ListView class="h-full" v-bind="listOptions"> </ListView>
	</div>

	<ImportTableDialog v-model="showImportTableDialog" />
</template>
