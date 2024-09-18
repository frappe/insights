import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import { createToast } from '../helpers/toasts'
import { QueryResultColumn } from '../types/query.types'

export type DataSourceTable = { table_name: string; data_source: string }
const tables = ref<DataSourceTable[]>([])

const loading = ref(false)
async function getTables(data_source?: string, search_term?: string) {
	loading.value = true
	tables.value = await call('insights.api.data_sources.get_data_source_tables', {
		data_source,
		search_term,
	})
	loading.value = false
	return tables.value
}

async function getTableColumns(data_source: string, table_name: string) {
	return call('insights.api.data_sources.get_data_source_table_columns', {
		data_source,
		table_name,
	}).then((columns: any[]) => {
		return columns.map((c) => ({
			name: c.column,
			type: c.type,
		})) as QueryResultColumn[]
	})
}

const updatingDataSourceTables = ref(false)
async function updateDataSourceTables(data_source: string) {
	updatingDataSourceTables.value = true
	createToast({
		message: `Updating tables for ${data_source}`,
		variant: 'info',
	})
	return call('insights.api.data_sources.update_data_source_tables', { data_source })
		.then(() => {
			getTables(data_source)
			createToast({
				message: `Tables updated for ${data_source}`,
				variant: 'success',
			})
		})
		.catch((e: Error) => {
			showErrorToast(e)
		})
		.finally(() => {
			updatingDataSourceTables.value = false
		})
}

type TableLink = {
	left_table: string
	right_table: string
	left_column: string
	right_column: string
}
async function getTableLinks(
	data_source: string,
	left_table: string,
	right_table: string
): Promise<TableLink[]> {
	return call('insights.api.data_sources.get_table_links', {
		data_source,
		left_table,
		right_table,
	})
}

export default function useTableStore() {
	return reactive({
		tables,
		loading,
		getTables,
		getTableColumns,
		updatingDataSourceTables,
		updateDataSourceTables,
		getTableLinks,
	})
}
