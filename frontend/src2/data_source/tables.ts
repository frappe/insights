import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast, toOptions } from '../helpers'
import { createToast } from '../helpers/toasts'
import { QueryResultColumn, QueryResultRow } from '../types/query.types'

export type DataSourceTable = {
	name: string
	table_name: string
	data_source: string
	preview?: any[]
}
const tables = ref<Record<string, DataSourceTable[]>>({})

const loading = ref(false)
export async function getTables(data_source?: string, search_term?: string, limit: number = 100) {
	loading.value = true
	const _tables = await call('insights.api.data_sources.get_data_source_tables', {
		data_source,
		search_term,
		limit,
	})
	loading.value = false
	if (data_source) {
		tables.value[data_source] = _tables
	} else {
		tables.value['__all'] = _tables
	}
	return _tables
}

const fetchingTable = ref(false)
export type DataSourceTablePreview = {
	table_name: string
	data_source: string
	columns: QueryResultColumn[]
	rows: QueryResultRow[]
}
async function fetchTable(
	data_source: string,
	table_name: string
): Promise<DataSourceTablePreview> {
	fetchingTable.value = true
	return call('insights.api.data_sources.get_data_source_table', {
		data_source,
		table_name,
	})
		.catch((e: Error) => {
			showErrorToast(e)
		})
		.finally(() => {
			fetchingTable.value = false
		})
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

export async function getRowCount(data_source: string, table_name: string) {
	return call('insights.api.data_sources.get_data_source_table_row_count', {
		data_source,
		table_name,
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

async function updateTableLinks(data_source: string) {
	createToast({
		title: 'Updating table links',
		message: `Updating table links for ${data_source}. This may take a while.`,
		variant: 'info',
	})
	return call('insights.api.data_sources.update_table_links', { data_source }).then(() => {
		createToast({
			message: `Table links updated for ${data_source}`,
			variant: 'success',
		})
	})
}

export function getTableOptions(data_source: string) {
	if (!tables.value[data_source]) return []
	return toOptions(tables.value[data_source], {
		label: 'table_name',
		value: 'table_name',
		description: 'data_source',
	})
}

export default function useTableStore() {
	return reactive({
		tables,
		loading,
		getTables,
		getRowCount,
		getOptions: getTableOptions,

		getTableColumns,
		updatingDataSourceTables,
		updateDataSourceTables,

		getTableLinks,
		updateTableLinks,

		fetchingTable,
		fetchTable,
	})
}
