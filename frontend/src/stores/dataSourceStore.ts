import * as api from '@/api'
import dayjs from '@/utils/dayjs'
import { defineStore } from 'pinia'
import { computed } from 'vue'

const useDataSourceStore = defineStore('insights:data_sources', () => {
	const listResource = api.getListResource({
		doctype: 'Insights Data Source',
		cache: 'dataSourceList',
		filters: {},
		fields: ['name', 'title', 'status', 'creation', 'modified', 'is_site_db', 'database_type'],
		orderBy: 'creation desc',
		auto: true,
	})

	const list = computed<DataSourceListItem[]>(
		() =>
			listResource.list.data?.map((dataSource: DataSourceListItem) => {
				dataSource.created_from_now = dayjs(dataSource.creation).fromNow()
				dataSource.modified_from_now = dayjs(dataSource.modified).fromNow()
				dataSource.title =
					dataSource.is_site_db && dataSource.title == 'Site DB'
						? window.location.hostname
						: dataSource.title
				return dataSource
			}) || []
	)
	const dropdownOptions = computed<DropdownOption[]>(() =>
		list.value.map((dataSource: DataSourceListItem) => ({
			label: dataSource.title,
			value: dataSource.name,
			description: dataSource.database_type,
		}))
	)

	return {
		list,
		dropdownOptions,
		loading: listResource.list.loading,
		testing: api.testDataSourceConnection.loading,
		creating: api.createDataSource.loading,
		deleting: listResource.delete.loading,
		create: (args: any) => api.createDataSource.submit(args).then(() => listResource.list.reload()),
		delete: (name: string) => listResource.delete.submit(name).then(() => listResource.list.reload()),
		testConnection: (args: any) => api.testDataSourceConnection.submit(args),
	}
})

export default useDataSourceStore
export type DataSourceStore = ReturnType<typeof useDataSourceStore>
