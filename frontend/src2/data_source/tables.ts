import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { QueryResultColumn } from '../types/query.types'
import { createToast } from '../helpers/toasts'

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

const updatingDataSourceTables = ref(false)
async function updateDataSourceTables(data_source: string) {
	updatingDataSourceTables.value = true
	return call(basePath + 'update_data_source_tables', { data_source })
		.then(() => {
			getTables(data_source)
		})
		.finally(() => {
			updatingDataSourceTables.value = false
			createToast({
				message: `Tables updated for ${data_source}`,
				variant: 'success',
			})
		})
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
		updatingDataSourceTables,
		updateDataSourceTables,
	})
}
