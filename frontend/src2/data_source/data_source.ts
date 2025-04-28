import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { defineAsyncComponent, h, reactive, ref } from 'vue'
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
		title: source.is_site_db && source.title == 'Site DB' ? window.location.hostname : source.title,
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

export function getDataSourceOptions() {
	const list = getDataSourceList()
	return toOptions(list.value, {
		label: 'title',
		value: 'name',
		description: 'database_type',
	})
}

function getSchema(data_source: string) {
	return call('insights.api.data_sources.get_schema', { data_source })
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

		getSchema,

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
	if (database_type === 'SQLite') {
		comp = defineAsyncComponent(() => import('../components/Icons/SQLiteIcon.vue'))
	}
	if (database_type === 'DuckDB') {
		comp = defineAsyncComponent(() => import('../components/Icons/DuckDBIcon.vue'))
	}
	return comp
		? h(comp, {
				class: size === 'sm' ? 'w-5 h-5' : 'w-8 h-8',
		  })
		: null
}
