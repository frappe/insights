import { getDocumentResource } from '@/api'
import useCacheStore from '@/stores/cacheStore'
import { computed, reactive, ref, UnwrapRef } from 'vue'

function useDataSource(name: string) {
	const cacheStore = useCacheStore()
	if (cacheStore.getDataSource(name)) {
		return cacheStore.getDataSource(name)
	}

	const resource: DataSourceResource = getDocumentResource('Insights Data Source', name)
	resource.fetchIfNeeded()

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

	const groupedTableOptions = computed<DataSourceTableGroupedOption[]>(() => {
		const tablesByGroup = tableList.value.filter((t) => !t.hidden).reduce((acc, table) => {
			const group = table.is_query_based ? 'Query-based tables' : 'Tables'
			if (!acc[group]) acc[group] = []
			acc[group].push(table)
			return acc
		}, {} as Record<string, DataSourceTableListItem[]>)

		return Object.entries(tablesByGroup).map(([group, tables]) => {
			return {
				group,
				items: tables.map((table) => {
					return {
						table: table.table,
						value: table.table,
						label: table.label,
						description: table.table,
						data_source: name,
					}
				}),
			}
		})
	})

	function updateTableRelationship(tableRelationship: TableRelationship) {
		return resource.update_table_link.submit({ data: tableRelationship })
	}
	function deleteTableRelationship(tableRelationship: TableRelationship) {
		return resource.delete_table_link.submit({ data: tableRelationship })
	}

	const dataSource: DataSource = reactive({
		doc,
		tableList,
		dropdownOptions,
		groupedTableOptions,
		loading: resource.loading,
		fetchTables,
		updateTableRelationship,
		deleteTableRelationship,
		syncTables: () => resource.enqueue_sync_tables.submit(),
		delete: () => resource.delete.submit(),
	})

	cacheStore.setDataSource(name, dataSource)
	return dataSource
}

type TableRelationship = {
	primary_table: string
	secondary_table: string
	primary_column: string
	secondary_column: string
	cardinality: string
}

export default useDataSource
export type DataSource = UnwrapRef<{
	doc: object
	tableList: DataSourceTableListItem[]
	dropdownOptions: DataSourceTableOption[]
	groupedTableOptions: DataSourceTableGroupedOption[]
	loading: boolean
	fetchTables: () => Promise<DataSourceTableListItem[]>
	updateTableRelationship: (tableRelationship: TableRelationship) => Promise<any>
	deleteTableRelationship: (tableRelationship: TableRelationship) => Promise<any>
	syncTables: () => Promise<any>
	delete: () => Promise<any>
}>
