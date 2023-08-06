declare module 'frappe-ui'
declare module '@/utils/dayjs'

interface User {
	user_id: string
	first_name: string
	last_name: string
	full_name: string
	user_image: string
	is_admin: boolean
	is_user: boolean
}

interface AuthState {
	initialized: boolean
	user: User
}

type ListResourceParams = {
	type?: 'list'
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
	list: {
		data: any[]
		loading: boolean
		reload: () => void
	},
	delete: Resource
}

type Resource = {
	data: any
	loading: boolean
	submit: (args: any) => Promise<any>
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

type DropdownOption = {
	label: string
	value: string
	description: string
}
