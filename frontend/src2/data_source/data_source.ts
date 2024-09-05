import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { useTimeAgo } from '@vueuse/core'
import { DataSource, DataSourceListItem } from './data_source.types'
import { showErrorToast } from '../helpers'


const sources = ref<DataSourceListItem[]>([])

const loading = ref(false)
async function getSources() {
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
		.catch((error: Error) => {
			showErrorToast(error)
		})
		.finally(() => {
			creating.value = false
		})
}

export default function useDataSourceStore() {
	if (!sources.value.length) {
		getSources()
	}

	return reactive({
		sources,
		loading,
		getSources,

		testing,
		testConnection,

		creating,
		createDataSource,
	})
}
