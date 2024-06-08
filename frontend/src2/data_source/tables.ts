import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'

const basePath = 'insights.insights.doctype.insights_data_source.insights_data_source.'

type DataSourceTable = { table_name: string; data_source: string }
const tables = ref<DataSourceTable[]>([])

const loading = ref(false)
async function getTables(data_source?: string, search_term?: string) {
	loading.value = true
	tables.value = await call(basePath + 'get_data_source_tables', {
		data_source,
		search_term,
	})
	loading.value = false
	return tables.value
}

async function getTableColumns(
	data_source: string,
	table_name: string
): Promise<QueryResultColumn[]> {
	return call(basePath + 'get_table_columns', { data_source, table_name }).then(
		(columns: any[]) => {
			return columns.map((c) => ({
				name: c.column,
				type: c.type,
			}))
		}
	)
}

export default function useTableStore() {
	if (!tables.value.length) {
		getTables()
	}

	return reactive({
		tables,
		loading,
		getTables,
		getTableColumns,
	})
}
