import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { defineAsyncComponent, h, reactive, ref, watch, type Ref } from 'vue'
import { showErrorToast, toOptions } from '../helpers'
import { DatabaseType, DataSource, DataSourceListItem } from './data_source.types'

const sources = ref<DataSourceListItem[]>([])

const loading = ref(false)
async function fetchSources() {
	loading.value = true
	sources.value = await call('insights.api.data_sources.get_all_data_sources')
	sources.value = sources.value.map((source: any) => ({
		...source,
		created_from_now: useTimeAgo(source.creation),
		modified_from_now: useTimeAgo(source.modified),
	}))
	loading.value = false
	return sources.value
}
function getSource(name: string) {
	return sources.value.find((source) => source.name === name)
}

const testing = ref(false)
function testConnection(data_source: DataSource) {
	testing.value = true
	return call('insights.api.data_sources.test_connection', { data_source })
		.catch((error: Error) => {
			showErrorToast(error, false)
		})
		.finally(() => {
			testing.value = false
		})
}

const creating = ref(false)
function createDataSource(data_source: DataSource) {
	creating.value = true
	return call('insights.api.data_sources.create_data_source', { data_source })
		.then(() => {
			fetchSources()
		})
		.catch((error: Error) => {
			showErrorToast(error)
		})
		.finally(() => {
			creating.value = false
		})
}

export function getDataSourceList() {
	if (!sources.value.length && !loading.value) {
		fetchSources()
	}
	return sources
}

/**
 * A table's name as its users know it. A Frappe database names a doctype's
 * table `tab` and the doctype, so `tabSales Invoice` reads as Sales Invoice.
 */
export function tableLabel(table: { data_source: string; table_name: string }) {
	const source = getDataSourceList().value.find((s) => s.name === table.data_source)
	return source?.is_frappe_db ? table.table_name.replace(/^tab/, '') : table.table_name
}

export function getDataSourceOptions() {
	const list = getDataSourceList()
	return toOptions(list.value, {
		label: 'title',
		value: 'name',
		description: 'database_type',
	})
}

export type SourceSchema = Record<
	string,
	{ label?: string; columns: { label: string; detail: string; type: string }[] }
>

/** The tables and columns of the source picked, and whether they are on their way or failed. */
export function useSourceSchema(source: Ref<string>) {
	const state = reactive({ schema: {} as SourceSchema, loading: false, failed: false })
	let fetches = 0
	watch(
		source,
		(data_source) => {
			const token = ++fetches
			state.schema = {}
			state.failed = false
			state.loading = Boolean(data_source)
			if (!data_source) return
			call<SourceSchema>('insights.api.data_sources.get_schema', { data_source })
				.then((schema: SourceSchema) => {
					if (token === fetches) state.schema = schema
				})
				.catch((error: Error) => {
					if (token !== fetches) return
					state.failed = true
					showErrorToast(error, false)
				})
				.finally(() => token === fetches && (state.loading = false))
		},
		{ immediate: true },
	)
	return state
}

export default function useDataSourceStore() {
	if (!sources.value.length && !loading.value) {
		fetchSources()
	}

	return reactive({
		sources,
		loading,
		getSources: fetchSources,
		getSource,
		getOptions: getDataSourceOptions,

		testing,
		testConnection,

		creating,
		createDataSource,
	})
}

export function getDatabaseLogo(database_type: DatabaseType, size: 'sm' | 'md' = 'md') {
	let comp = undefined
	if (database_type === 'MariaDB') {
		comp = defineAsyncComponent(() => import('../components/Icons/MariaDBIcon.vue'))
	}
	if (database_type === 'PostgreSQL') {
		comp = defineAsyncComponent(() => import('../components/Icons/PostgreSQLIcon.vue'))
	}
	if (database_type === 'ClickHouse') {
		comp = defineAsyncComponent(() => import('../components/Icons/ClickHouseIcon.vue'))
	}
	if (database_type === 'SQLite') {
		comp = defineAsyncComponent(() => import('../components/Icons/SQLiteIcon.vue'))
	}
	if (database_type === 'DuckDB') {
		comp = defineAsyncComponent(() => import('../components/Icons/DuckDBIcon.vue'))
	}

	let sizeClass = size === 'sm' ? 'size-5' : 'size-8'
	if (size == 'sm' && database_type === 'ClickHouse') {
		sizeClass = 'size-4'
	}
	return comp ? h(comp, { class: sizeClass }) : null
}
