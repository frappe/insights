import { DataSource } from '@/datasource/useDataSource'
import { DataSourceTable } from '@/datasource/useDataSourceTable'
import { defineStore } from 'pinia'
import { ref } from 'vue'

type DataSourceCache = Record<string, DataSource>
type TableCache = Record<string, DataSourceTable>

const useCacheStore = defineStore('insights:cache', () => {
	const dataSourceCache = ref<DataSourceCache>({})
	function getDataSource(name: string) {
		return dataSourceCache.value[name]
	}
	function setDataSource(name: string, dataSource: DataSource) {
		dataSourceCache.value[name] = dataSource
	}

	const tableCache = ref<TableCache>({})
	function getTable(name: string) {
		return tableCache.value[name]
	}
	function setTable(name: string, table: DataSourceTable) {
		tableCache.value[name] = table
	}

	return {
		getDataSource,
		setDataSource,
		getTable,
		setTable,
	}
})

export default useCacheStore
