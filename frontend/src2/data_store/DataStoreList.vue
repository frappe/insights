<script setup lang="ts">
import { Breadcrumbs, Button } from 'frappe-ui'
import { ChevronRightIcon, PlusIcon, RefreshCwIcon, SearchIcon } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { getDatabaseLogo } from '../data_source/data_source'
import type { DatabaseType } from '../data_source/data_source.types'
import useDataStore, { DataStoreTable, SyncLog } from './data_store'
import ImportTableDialog from './ImportTableDialog.vue'
import SyncDialog from './SyncDialog.vue'
import SyncLogSummary from './SyncLogSummary.vue'
import session from '../session'
import { __ } from '../translation'

const dataStore = useDataStore()
const searchQuery = ref('')
const showImportTableDialog = ref(false)
const showSyncDialog = ref(false)
const syncDialogTable = ref<DataStoreTable | null>(null)
const expandedTable = ref<string | null>(null)
const syncLogs = ref<Record<string, SyncLog | null>>({})

onMounted(() => dataStore.getTables())

const tables = computed(() => dataStore.tables['__all'] || [])

const filteredTables = computed(() => {
	const query = searchQuery.value.toLowerCase().trim()
	if (!query) return tables.value
	return tables.value.filter((t: DataStoreTable) => t.table_name.toLowerCase().includes(query))
})

function tableKey(table: DataStoreTable) {
	return `${table.data_source}:${table.table_name}`
}

function isExpanded(table: DataStoreTable) {
	return expandedTable.value === tableKey(table)
}

function toggleExpand(table: DataStoreTable) {
	const key = tableKey(table)
	if (expandedTable.value === key) {
		expandedTable.value = null
		return
	}
	expandedTable.value = key
	if (!(key in syncLogs.value)) {
		dataStore.getLastSyncLog(table.data_source, table.table_name).then((log) => {
			syncLogs.value[key] = log
		})
	}
}

function openSyncDialog(table: DataStoreTable) {
	syncDialogTable.value = table
	showSyncDialog.value = true
}

const logoCache = new Map()
function getCachedLogo(dbType: DatabaseType) {
	if (!logoCache.has(dbType)) {
		logoCache.set(dbType, getDatabaseLogo(dbType, 'sm'))
	}
	return logoCache.get(dbType)
}
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: __('Data Store'), route: '/data-store' }]" />
		<div class="flex items-center gap-2">
			<Button
				v-if="session.user.is_admin"
				:label="__('Import Table')"
				variant="solid"
				@click="showImportTableDialog = true"
			>
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl :placeholder="__('Search table')" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>

		<div
			v-if="!filteredTables.length"
			class="flex flex-1 flex-col items-center justify-center gap-2 text-gray-500"
		>
			<p class="text-sm">{{ __('No tables found') }}</p>
			<Button
				v-if="session.user.is_admin && !searchQuery"
				:label="__('Import Table')"
				variant="solid"
				@click="showImportTableDialog = true"
			>
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>

		<div v-else class="flex flex-col">
			<div
				class="flex items-center gap-3 rounded bg-gray-50 px-4 py-2 text-sm font-medium text-gray-600"
			>
				<div class="w-5"></div>
				<div style="flex: 2">{{ __('Table') }}</div>
				<div style="flex: 1; min-width: 140px">{{ __('Data Source') }}</div>
				<div style="min-width: 120px">{{ __('Last Synced') }}</div>
				<div class="w-8"></div>
			</div>

			<div class="flex flex-col divide-y">
				<div v-for="table in filteredTables" :key="tableKey(table)" class="flex flex-col">
					<div
						class="flex cursor-pointer items-center gap-3 px-4 py-2.5 hover:bg-gray-50"
						@click="toggleExpand(table)"
					>
						<ChevronRightIcon
							class="h-4 w-4 flex-shrink-0 text-gray-400"
							:class="{ 'rotate-90': isExpanded(table) }"
							stroke-width="1.5"
						/>

						<div class="min-w-0" style="flex: 2">
							<p class="truncate text-sm font-medium text-gray-900">
								{{ table.table_name }}
							</p>
						</div>

						<div
							class="flex items-center gap-1.5 text-sm text-gray-600"
							style="flex: 1; min-width: 140px"
						>
							<component :is="getCachedLogo(table.database_type)" />
							<span class="truncate">{{ table.data_source }}</span>
						</div>

						<div class="text-sm text-gray-500" style="min-width: 120px">
							{{ table.last_synced_from_now || __('Never') }}
						</div>

						<Button
							v-if="session.user.is_admin"
							variant="ghost"
							size="sm"
							@click.stop="openSyncDialog(table)"
						>
							<template #icon>
								<RefreshCwIcon
									class="h-3.5 w-3.5 text-gray-600"
									stroke-width="1.5"
								/>
							</template>
						</Button>
					</div>

					<SyncLogSummary
						v-if="isExpanded(table)"
						:log="syncLogs[tableKey(table)]"
						:sync-mode="table.sync_mode"
					/>
				</div>
			</div>
		</div>
	</div>

	<ImportTableDialog v-model="showImportTableDialog" />
	<SyncDialog v-model="showSyncDialog" :table="syncDialogTable" />
</template>
