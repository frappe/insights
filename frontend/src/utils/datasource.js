import { createDocumentResource, createResource } from 'frappe-ui'
import { reactive, watch, computed, inject } from 'vue'

const dataSourceResource = createResource({
	method: 'insights.api.get_data_source',
	initalData: {},
})

export function useDataSource(name) {
	const dataSource = reactive({})

	dataSourceResource.fetch({ name })
	watch(
		() => dataSourceResource.data,
		(data) => Object.assign(dataSource, data)
	)

	return dataSource
}

export function useDataSourceTable(name) {
	const $notify = inject('$notify')
	const dataSourceTable = createDocumentResource({
		doctype: 'Insights Table',
		name: name,
		whitelistedMethods: {
			syncTable: 'sync_table',
			updateVisibility: 'update_visibility',
			getPreview: 'get_preview',
		},
	})
	dataSourceTable.getPreview.submit()
	dataSourceTable.rows = computed(() => dataSourceTable.getPreview.data?.message || {})
	dataSourceTable.sync = () => {
		dataSourceTable.syncing = true
		dataSourceTable.syncTable.submit().then(() => {
			dataSourceTable.syncing = false
		})
	}

	return dataSourceTable
}
