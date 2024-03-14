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
	const queryList = ref<QueryAsTableListItem[]>([])
	const dropdownOptions = ref<DataSourceTableOption[]>([])
	const groupedTableOptions = ref<DataSourceTableGroupedOption[]>([])

	async function fetchTables() {
		const promises = [resource.get_tables.submit(), resource.get_queries.submit()]
		const responses = await Promise.all(promises)
		tableList.value = responses[0]
		queryList.value = responses[1]
		dropdownOptions.value = makeDropdownOptions()
		groupedTableOptions.value = makeGroupedTableOptions()
		return tableList.value
	}

	function makeDropdownOptions() {
		return (
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
	}

	function makeGroupedTableOptions() {
		const tablesByGroup: Record<string, DataSourceTableOption[]> = {
			Tables: [],
			Queries: [],
		}

		tableList.value
			.filter((t) => !t.hidden && !t.is_query_based)
			.forEach((table: DataSourceTableListItem) => {
				tablesByGroup['Tables'].push({
					table: table.table,
					label: table.label,
					value: table.table,
					description: table.table,
					data_source: name,
				})
			})

		queryList.value.forEach((query: QueryAsTableListItem) => {
			tablesByGroup['Queries'].push({
				table: query.name,
				label: query.title,
				value: query.name,
				description: query.name,
				data_source: name,
			})
		})

		return Object.entries(tablesByGroup).map(([group, tables]) => {
			return { group, items: tables }
		})
	}

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
