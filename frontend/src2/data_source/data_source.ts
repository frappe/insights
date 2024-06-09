import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'

const basePath = 'insights.insights.doctype.insights_data_source_v3.insights_data_source_v3.'

type DataSource = { title: string; name: string }
const sources = ref<DataSource[]>([])

const loading = ref(false)
async function getSources() {
	loading.value = true
	sources.value = await call(basePath + 'get_data_sources')
	loading.value = false
	return sources.value
}


export default function useDataSourceStore() {
	if (!sources.value.length) {
		getSources()
	}

	return reactive({
		sources,
		loading,
		getSources,
	})
}
