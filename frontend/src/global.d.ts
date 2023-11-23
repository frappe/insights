declare module 'frappe-ui'
declare module '@/utils/dayjs'

declare type HashString = `#${string}`
declare type RGBString = `rgb(${number}, ${number}, ${number})`

interface User {
	user_id: string
	first_name: string
	last_name: string
	full_name: string
	user_image: string
	is_admin: boolean
	is_user: boolean
	country: string
	locale: string
}

interface Session {
	initialized: boolean
	user: User
}

type ListResourceParams = {
	type?: 'list'
	url?: string
	auto?: boolean
	doctype: string
	filters: any
	fields: string[]
	orderBy: string
	cache?: string
	start?: number
	pageLength?: number
	groupBy?: string
}

type ListResource = {
	filters: any
	list: {
		data: any[]
		loading: boolean
		reload: () => void
	}
	delete: Resource
}

type Resource = {
	data: any
	loading: boolean
	submit: (args?: any) => Promise<any>
}

type DataSourceListItem = {
	name: string
	title: string
	status: string
	is_site_db: boolean
	database_type: string
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
}

type DocumentResource = {
	doc: object
	loading: boolean
	get: Resource
	delete: Resource
	fetchIfNeeded: () => Promise<any>
}

interface DataSourceResource extends DocumentResource {
	get_tables: Resource
	get_queries: Resource
	enqueue_sync_tables: Resource
	update_table_link: Resource
	delete_table_link: Resource
}

interface TableResource extends DocumentResource {
	updateVisibility: Resource
	getPreview: Resource
	syncTable: Resource
	update_column_type: Resource
}

type DropdownOption = {
	label: string
	value: string
	description: string
}

interface DataSourceTableOption extends DropdownOption {
	data_source: string
	table: string
}

interface DataSourceTableListItem {
	table: string
	label: string
	hidden: boolean
	is_query_based: boolean
}

type GroupedDropdownOption = {
	group: string
	items: DropdownOption[]
}

interface DataSourceTableGroupedOption extends GroupedDropdownOption {
	items: DataSourceTableOption[]
}

interface QueryAsTableListItem {
	name: string
	title: string
	data_source: string
}