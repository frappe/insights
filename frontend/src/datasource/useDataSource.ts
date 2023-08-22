import { getDocumentResource } from '@/api'
import useCacheStore from '@/stores/cacheStore'
import { computed, reactive, ref, UnwrapRef } from 'vue'

function useDataSource(name: string) {
	const cacheStore = useCacheStore()
	if (cacheStore.getDataSource(name)) {
		return cacheStore.getDataSource(name)
	}

	const resource: DataSourceResource = getDocumentResource('Insights Data Source', name)
	resource.triggerFetch()

	const doc = computed({
		get: () => resource.doc || {},
		set: (value: object) => (resource.doc = value),
	})

	const tableList = ref<DataSourceTableListItem[]>([])
	async function fetchTables() {
		const response = await resource.get_tables.submit()
		tableList.value = response.message
		return tableList.value
	}

	const dropdownOptions = computed<DataSourceTableOption[]>(() =>
		tableList.value
			.filter((t) => !t.hidden)
			// remove duplicates
			.filter((sourceTable, index, self) => {
				return (
					self.findIndex((t) => {
						return t.table === sourceTable.table
					}) === index
				)
			})
			.map((sourceTable) => {
				return {
					table: sourceTable.table,
					value: sourceTable.table,
					label: sourceTable.label,
					description: sourceTable.table,
					data_source: name,
				}
			})
	)

	const dataSource: DataSource = reactive({
		doc,
		tableList,
		dropdownOptions,
		loading: resource.loading,
		fetchTables,
		syncTables: () => resource.enqueue_sync_tables.submit(),
		delete: () => resource.delete.submit(),
	})

	cacheStore.setDataSource(name, dataSource)
	return dataSource
}

export default useDataSource
export type DataSource = UnwrapRef<{
	doc: object
	tableList: DataSourceTableListItem[]
	dropdownOptions: DataSourceTableOption[]
	loading: boolean
	fetchTables: () => Promise<DataSourceTableListItem[]>
	syncTables: () => Promise<any>
	delete: () => Promise<any>
}>
