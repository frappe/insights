import { FilterType } from '../helpers/constants'
import { ChartConfig, ChartType } from './chart.types'
import { FilterGroupArgs, FilterOperator, FilterValue, Operation, OrderByArgs } from './query.types'

export interface QueryVariable {
	variable_name: string
	variable_value: string
}

export type WorkbookListItem = {
	title: string
	name: string
	owner: string
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
	views: number
	shared_with: string[]
	shared_with_organization?: boolean
}

export type WorkbookQuery = {
	name: string
	title: string
	is_native_query?: boolean
	is_script_query?: boolean
	is_builder_query?: boolean
}

export type WorkbookChart = {
	name: string
	title: string
	query: string
	chart_type: ChartType
}

export type WorkbookDashboard = {
	name: string
	title: string
}

export type InsightsWorkbook = {
	doctype: 'Insights Workbook'
	name: string
	owner: string
	title: string
	queries: WorkbookQuery[]
	charts: WorkbookChart[]
	dashboards: WorkbookDashboard[]
	read_only: boolean
}

export type InsightsQueryv3 = {
	doctype: 'Insights Query v3'
	name: string
	owner: string
	title: string
	workbook: string
	operations: Operation[]
	variables?: QueryVariable[]
	use_live_connection?: boolean
	is_native_query?: boolean
	is_script_query?: boolean
	is_builder_query?: boolean
	read_only: boolean
}

export type InsightsChartv3 = {
	doctype: 'Insights Chart v3'
	name: string
	owner: string
	title: string
	workbook: string
	query: string
	data_query: string
	chart_type: ChartType
	is_public: boolean
	operations: Operation[]
	use_live_connection?: boolean
	config: ChartConfig & {
		order_by: OrderByArgs[]
		filters?: FilterGroupArgs
		limit?: number
	}
	read_only: boolean
}

export type InsightsDashboardv3 = {
	doctype: 'Insights Dashboard v3'
	name: string
	owner: string
	title: string
	workbook: string
	items: WorkbookDashboardItem[]
	preview_image?: string
	share_link?: string
	is_public: boolean
	is_shared_with_organization: boolean
	people_with_access: {
		email: string
		full_name: string
		user_image: string
	}[]
	read_only: boolean
}

export type WorkbookDashboardItem =
	| WorkbookDashboardChart
	| WorkbookDashboardText
	| WorkbookDashboardFilter

export type Layout = {
	i: string
	x: number
	y: number
	w: number
	h: number
}
export type WorkbookDashboardChart = {
	type: 'chart'
	chart: string
	layout: Layout
}
export type WorkbookDashboardFilter = {
	type: 'filter'
	filter_name: string
	filter_type: FilterType
	links: Record<string, string>
	default_operator?: FilterOperator
	default_value?: FilterValue
	layout: Layout
}
export type WorkbookDashboardText = {
	type: 'text'
	text: string
	layout: Layout
}

export type ShareAccess = 'view' | 'edit' | undefined
export type WorkbookSharePermission = {
	email: string
	full_name: string
	access: ShareAccess
}
