import { call, createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'
import { setOrGet } from '../utils'

const datasources = {}

export function useDataSource(name) {
	return setOrGet(datasources, name, makeDataSource, [name])
}

function makeDataSource(name) {
	let resource = getDataSourceResource(name)
	const state = reactive({
		doc: {},
		tables: [],
		loading: true,
	})

	state.reload = () => {
		return resource.get.fetch().then((doc) => {
			state.loading = false
			state.doc = doc
		})
	}
	state.reload()

	state.fetch_tables = async () => {
		const response = await resource.get_tables.submit()
		state.tables = response.message
		return state.tables
	}
	state.sync_tables = () => {
		return resource.enqueue_sync_tables.submit()
	}
	state.delete = () => {
		return resource.delete.submit()
	}
	state.change_data_source = (data_source) => {
		resource = getDataSourceResource(data_source)
		state.reload()
	}

	return state
}

const datasource_tables = {}
const cached_tablenames = {}

export async function useDataSourceTable({ name, data_source, table }) {
	const _name = name || cached_tablenames[data_source + table]
	if (_name) {
		return setOrGet(datasource_tables, _name, makeDataSourceTable, [_name])
	}
	const tablename = await getTableName(data_source, table)
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
			doc.columns = doc.columns.map((c) => {
				c.data_source = doc.data_source
				c.table_label = doc.label
				c.table = doc.table
				return c
			})
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

async function getTableName(data_source, table) {
	const name = await call('insights.api.get_table_name', {
		data_source: data_source,
		table: table,
	})
	// cache the name
	cached_tablenames[data_source + table] = name
	return name
}
