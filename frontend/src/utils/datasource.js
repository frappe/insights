import { createResource } from 'frappe-ui'
import { reactive, watch } from 'vue'

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

const dataSourceTableResource = createResource({
	method: 'insights.api.get_data_source_table',
	initalData: {},
})
const dataSourceTableUpdateResource = createResource({
	method: 'insights.api.update_data_source_table',
	initalData: {},
})

export function useDataSourceTable(name, table) {
	const dataSourceTable = reactive({
		updateVisibility,
	})

	dataSourceTableResource.fetch({ name, table })
	watch(
		() => dataSourceTableResource.data,
		(data) => Object.assign(dataSourceTable, data)
	)

	function updateVisibility(hidden) {
		dataSourceTableUpdateResource.submit({ name, table, hidden })
	}

	return dataSourceTable
}
