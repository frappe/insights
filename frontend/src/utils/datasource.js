import { createDocumentResource, createResource } from 'frappe-ui'
import { reactive, watch, computed } from 'vue'

const dataSourceResource = createResource({
	url: 'insights.api.get_data_source',
	initalData: {},
})
const syncDataSourceResource = createResource({
	url: 'insights.api.sync_data_source',
	initalData: {},
})

export function useDataSource(name) {
	const dataSource = reactive({})

	dataSourceResource.fetch({ name })
	watch(
		() => dataSourceResource.data,
		(data) => Object.assign(dataSource, data)
	)
	dataSource.syncTables = () => {
		return syncDataSourceResource.submit({ data_source: name })
	}

	return dataSource
}

export function useDataSourceTable(name) {
	const dataSourceTable = createDocumentResource({
		doctype: 'Insights Table',
		name: name,
		whitelistedMethods: {
			syncTable: 'sync_table',
			updateVisibility: 'update_visibility',
			getPreview: 'get_preview',
			update_column_type: 'update_column_type',
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
