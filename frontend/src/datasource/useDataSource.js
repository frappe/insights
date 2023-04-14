import { call, createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'
import { setOrGet } from '../utils'

const datasources = {}

export function useDataSource(name) {
	return setOrGet(datasources, name, makeDataSource, [name])
}

function makeDataSource(name) {
	const resource = getDataSourceResource(name)
	const state = reactive({
		doc: {},
		tables: [],
		loading: true,
	})
	resource.get.fetch().then((doc) => {
		state.loading = false
		state.doc = doc
	})

	state.fetch_tables = async () => {
		const response = await resource.get_tables.submit()
		state.tables = response.message.map((t) => ({ ...t, data_source: name }))
		return state.tables
	}
	state.sync_tables = () => {
		return resource.enqueue_sync_tables.submit()
	}
	state.delete = () => {
		return resource.delete.submit()
	}

	return state
}

const datasource_tables = {}
const datasource_tablenames = {}

export async function useDataSourceTable({ name, data_source, table }) {
	const _name = name || datasource_tablenames[data_source + table]
	if (_name) {
		return setOrGet(datasource_tables, _name, makeDataSourceTable, [_name])
	}
	const tablename = await call('insights.api.get_table_name', {
		data_source: data_source,
		table: table,
	})
	return setOrGet(datasource_tables, tablename, makeDataSourceTable, [tablename])
}

function makeDataSourceTable(name) {
	const dataSourceTable = createDocumentResource({
		doctype: 'Insights Table',
		name: name,
		whitelistedMethods: {
			syncTable: 'sync_table',
			updateVisibility: 'update_visibility',
			getPreview: 'get_preview',
			update_column_type: 'update_column_type',
		},
		transform: (doc) => {
			doc.columns = doc.columns.map((c) => ({ ...c, data_source: doc.data_source }))
			return doc
		},
	})
	dataSourceTable.get.fetch()
	dataSourceTable.getPreview.submit()
	dataSourceTable.rows = computed(() => dataSourceTable.getPreview.data?.message || {})
	dataSourceTable.sync = () => {
		dataSourceTable.syncing = true
		dataSourceTable.syncTable.submit().then(() => {
			dataSourceTable.syncing = false
		})
	}
	dataSourceTable.updateColumnType = (column) => {
		return dataSourceTable.update_column_type.submit({
			column: column.column,
			newtype: column.type,
		})
	}

	return dataSourceTable
}

function getDataSourceResource(name) {
	return createDocumentResource({
		doctype: 'Insights Data Source',
		name: name,
		whitelistedMethods: {
			enqueue_sync_tables: 'enqueue_sync_tables',
			get_tables: 'get_tables',
		},
	})
}
