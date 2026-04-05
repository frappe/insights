import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import { DatabaseType } from '../data_source/data_source.types'

export type SyncLog = {
	status: string
	rows_imported: number
	time_taken: number
	started_at: string
	ended_at: string
	error: string
	output: string
}

export type DataStoreTable = {
	name?: string
	data_source: string
	table_name: string
	database_type: DatabaseType
	last_synced_on: string
	last_synced_from_now: string
	sync_mode: string
	row_limit?: number
}
const storedTables = ref<Record<string, DataStoreTable[]>>({})

const loading = ref(false)
async function getTables(data_source?: string, search_term?: string, limit: number = 100) {
	loading.value = true
	return call('insights.api.data_store.get_data_store_tables', {
		data_source,
		search_term,
		limit,
	})
		.then((data: any) => {
			return data.map((d: any) => {
				d.last_synced_from_now = d.last_synced_on ? useTimeAgo(d.last_synced_on) : ''
				return d
			})
		})
		.then((_tables: DataStoreTable[]) => {
			if (data_source) {
				storedTables.value[data_source] = _tables
			} else {
				storedTables.value['__all'] = _tables
			}
			return _tables
		})
		.catch(showErrorToast)
		.finally(() => {
			loading.value = false
		})
}

const importingTable = ref(false)
async function importTable(data_source: string, table_name: string, row_limit?: number, sync_mode?: string) {
	importingTable.value = true
	return call('insights.api.data_store.import_table', {
		data_source,
		table_name,
		row_limit,
		sync_mode: sync_mode || '',
	})
		.then(() => {
			getTables(data_source)
		})
		.catch(showErrorToast)
		.finally(() => {
			importingTable.value = false
		})
}

async function syncTable(data_source: string, table_name: string) {
	return call('insights.api.data_store.import_table', {
		data_source,
		table_name,
		sync_mode: 'Incremental Sync',
	}).catch(showErrorToast)
}

async function fullRefreshTable(data_source: string, table_name: string) {
	return call('insights.api.data_store.import_table', {
		data_source,
		table_name,
		sync_mode: 'Full Refresh',
	}).catch(showErrorToast)
}

async function getLastSyncLog(data_source: string, table_name: string): Promise<SyncLog | null> {
	return call('insights.api.data_store.get_last_sync_log', {
		data_source,
		table_name,
	}).catch(showErrorToast)
}

export default function useDataStore() {
	return reactive({
		tables: storedTables,
		loading,
		getTables,

		importingTable,
		importTable,
		syncTable,
		fullRefreshTable,
		getLastSyncLog,
	})
}
