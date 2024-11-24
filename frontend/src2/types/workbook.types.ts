import { ChartConfig, ChartType } from './chart.types'
import { ColumnDataType, FilterGroupArgs, Measure, Operation, OrderByArgs } from './query.types'

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

export type InsightsWorkbook = {
	doctype: 'Insights Workbook'
	name: string
	owner: string
	title: string
	queries: WorkbookQuery[]
	charts: WorkbookChart[]
	dashboards: WorkbookDashboard[]
	enable_auto_save?: boolean
}

export type WorkbookQuery = {
	name: string
	title?: string
	operations: Operation[]
	use_live_connection?: boolean
	calculated_measures?: Record<string, Measure>
	is_native_query?: boolean
	is_script_query?: boolean
	is_builder_query?: boolean
}

export type WorkbookChart = {
	name: string
	title: string
	query: string
	is_public: boolean
	share_link?: string
	chart_type: ChartType
	config: ChartConfig & {
		order_by: OrderByArgs[]
		filters?: FilterGroupArgs
		limit?: number
	}
	operations: Operation[]
	use_live_connection?: boolean
	calculated_measures?: Record<string, Measure>
}

export type WorkbookDashboard = {
	name: string
	title: string
	items: WorkbookDashboardItem[]
	is_public?: boolean
	share_link?: string
}

export type WorkbookDashboardItem = WorkbookDashboardChart

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
	column: DashboardFilterColumn
	layout: Layout
}
export type WorkbookDashboardText = {
	type: 'text'
	text: string
	layout: Layout
}
export type DashboardFilterColumn = {
	query: string
	name: string
	type: ColumnDataType
}

export type ShareAccess = 'view' | 'edit' | undefined
export type WorkbookSharePermission = { email: string; full_name: string; access: ShareAccess }
