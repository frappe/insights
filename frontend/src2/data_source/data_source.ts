import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { useTimeAgo } from '@vueuse/core'
import { DataSource, DataSourceListItem } from './data_source.types'
import { showErrorToast } from '../helpers'

const basePath = 'insights.insights.doctype.insights_data_source_v3.insights_data_source_v3.'

const sources = ref<DataSourceListItem[]>([])

const loading = ref(false)
async function getSources() {
	loading.value = true
	sources.value = await call(basePath + 'get_data_sources')
	sources.value = sources.value.map((source: any) => ({
		...source,
		created_from_now: useTimeAgo(source.creation),
		modified_from_now: useTimeAgo(source.modified),
	}))
	loading.value = false
	return sources.value
}

const testing = ref(false)
function testConnection(data_source: DataSource) {
	testing.value = true
	return call(basePath + 'test_connection', { data_source })
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
	return call(basePath + 'create_data_source', { data_source })
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
