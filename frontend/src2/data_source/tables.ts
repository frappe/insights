import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { QueryResultColumn } from '../types/query.types'

const basePath = 'insights.insights.doctype.insights_data_source_v3.insights_data_source_v3.'

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

async function getTableColumns(data_source: string, table_name: string) {
	return call(basePath + 'get_table_columns', { data_source, table_name }).then(
		(columns: any[]) => {
			return columns.map((c) => ({
				name: c.column,
				type: c.type,
			})) as QueryResultColumn[]
		},
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
