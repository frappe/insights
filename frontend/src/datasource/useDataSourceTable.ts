import { fetchTableName, getDocumentResource } from '@/api'
import useCacheStore from '@/stores/cacheStore'
import { whenHasValue } from '@/utils'
import { useStorage } from '@vueuse/core'
import { UnwrapRef, computed, reactive } from 'vue'

export type GetTableParams = {
	name: string
	table: string
	data_source: string
}

async function useDataSourceTable(params: GetTableParams) {
	const name = await getTableName(params)

	const cacheStore = useCacheStore()
	if (cacheStore.getTable(name)) {
		return cacheStore.getTable(name)
	}

	const resource: TableResource = getDocumentResource('Insights Table', name)
	await resource.fetchIfNeeded()
	await whenHasValue(() => resource.doc)

	const doc = computed<any>({
		get: () => resource.doc || {},
		set: (value: any) => (resource.doc = value),
	})

	const columns = computed(() => {
		if (!doc.value?.columns) return []
		return doc.value.columns.map((column: any) => {
			return {
				column: column.column,
				type: column.type,
				label: column.label,
				table: doc.value.table,
				table_label: doc.value.label,
				data_source: doc.value.data_source,
			}
		})
	})

	const table: DataSourceTable = reactive({
		doc,
		columns,
		rows: computed(() => resource.getPreview.data),
		loading: resource.loading,
		syncing: resource.syncTable.loading,
		sync: () => resource.syncTable.submit(),
		fetchPreview: () => resource.getPreview.submit(),
		updateVisibility: (hidden: boolean) => {
			return resource.updateVisibility.submit({ hidden })
		},
		updateColumnType: (column: any) => {
			return resource.update_column_type.submit({
				column: column.column,
				newtype: column.type,
			})
		},
	})

	cacheStore.setTable(name, table)
	return table
}

const today = new Date().toISOString().split('T')[0]
const dailyCacheKey = `insights:table-name-cache-{${today}}`

for (const key of Object.keys(localStorage)) {
	if (key.startsWith('insights:table-name-cache-')) {
		localStorage.removeItem(key)
	}
}

type TableNameCache = Record<string, string>
const tableNameCache = useStorage<TableNameCache>(dailyCacheKey, {})

async function getTableName(params: GetTableParams): Promise<string> {
	const { name, table, data_source } = params
	if (name) return name

	const key = `${data_source}:${table}`
	if (tableNameCache.value[key]) {
		return tableNameCache.value[key]
	}

	const _name = await fetchTableName(data_source, table)
	tableNameCache.value[key] = _name
	return _name
}

export default useDataSourceTable
export type DataSourceTable = UnwrapRef<{
	doc: any
	columns: any[]
	rows: any[]
	loading: boolean
	syncing: boolean
	sync: () => Promise<any>
	fetchPreview: () => Promise<any>
	updateColumnType: (column: any) => Promise<any>
	updateVisibility: (hidden: boolean) => Promise<any>
}>
