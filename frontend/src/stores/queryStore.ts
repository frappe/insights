import * as api from '@/api'
import dayjs from '@/utils/dayjs'
import { VALID_CHARTS } from '@/widgets/widgets'
import { defineStore } from 'pinia'
import { computed } from 'vue'

type QueryListItem = {
	name: string
	title: string
	status: string
	is_assisted_query: boolean
	is_native_query: boolean
	is_script_query: boolean
	is_stored: boolean
	data_source: string
	data_source_title: string
	creation: string
	created_from_now: string
	owner: string
	owner_name: string
	owner_image: string
	chart_type: string
}

const useQueryStore = defineStore('insights:queries', () => {
	const listResource = api.getListResource({
		url: 'insights.api.queries.get_queries',
		doctype: 'Insights Query',
		cache: 'queryList',
		fields: FIELDS.map((f) => f.value),
		filters: {},
		auto: true,
		pageLength: 50,
		orderBy: 'creation desc',
	})

	const list = computed<QueryListItem[]>(
		() =>
			listResource.list.data?.map((query: QueryListItem) => {
				query.created_from_now = dayjs(query.creation).fromNow()
				return query
			}) || []
	)
	const dropdownOptions = computed<DropdownOption[]>(() => list.value.map(makeDropdownOption))

	function makeDropdownOption(query: QueryListItem): DropdownOption {
		return {
			label: query.title,
			value: query.name,
			description: query.data_source,
		}
	}

	async function createQuery(args: any) {
		return api.createQuery.submit(args).then((doc) => {
			listResource.list.reload()
			return doc
		})
	}

	async function deleteQuery(name: string) {
		return listResource.delete.submit(name).then(() => {
			listResource.list.reload()
		})
	}

	function reloadWithFilters(filters: any) {
		listResource.filters = filters
		listResource.list.reload()
	}

	return {
		list,
		dropdownOptions,
		loading: listResource.list.loading,
		creating: api.createQuery.loading,
		deleting: listResource.delete.loading,
		reload: () => listResource.list.reload(),
		create: createQuery,
		delete: deleteQuery,
		getFilterableFields: () => FIELDS,
		applyFilters: (filters: any) => reloadWithFilters(filters),
		getDropdownOptions: () => dropdownOptions.value,
	}
})

const FIELDS = [
	{
		label: 'Name',
		value: 'name',
		fieldname: 'name',
		fieldtype: 'Data',
	},
	{
		label: 'Title',
		value: 'title',
		fieldname: 'title',
		fieldtype: 'Data',
	},
	{
		label: 'Status',
		value: 'status',
		fieldname: 'status',
		fieldtype: 'Select',
		options: 'Pending Execution\nExecution Successful\nExecution Failed',
	},
	{
		label: 'Is Assisted Query',
		value: 'is_assisted_query',
		fieldname: 'is_assisted_query',
		fieldtype: 'Check',
	},
	{
		label: 'Is Native Query',
		value: 'is_native_query',
		fieldname: 'is_native_query',
		fieldtype: 'Check',
	},
	{
		label: 'Is Script Query',
		value: 'is_script_query',
		fieldname: 'is_script_query',
		fieldtype: 'Check',
	},
	{
		label: 'Is Stored',
		value: 'is_stored',
		fieldname: 'is_stored',
		fieldtype: 'Check',
	},
	{
		label: 'Data Source',
		value: 'data_source',
		fieldname: 'data_source',
		fieldtype: 'Link',
		options: 'Insights Data Source',
	},
	{
		label: 'Creation',
		value: 'creation',
		fieldname: 'creation',
		fieldtype: 'Datetime',
	},
	{
		label: 'Owner',
		value: 'owner',
		fieldname: 'owner',
		fieldtype: 'Link',
		options: 'User',
	},
	{
		label: 'Owner Name',
		value: 'owner_name',
		fieldname: 'owner_name',
		fieldtype: 'Data',
	},
	{
		label: 'Owner Image',
		value: 'owner_image',
		fieldname: 'owner_image',
		fieldtype: 'Data',
	},
	{
		label: 'Chart Type',
		value: 'chart_type',
		fieldname: 'chart_type',
		fieldtype: 'Select',
		options: VALID_CHARTS.join('\n'),
	},
]

export default useQueryStore
export type QueryStore = ReturnType<typeof useQueryStore>
