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

export type WorkbookFolder = {
	name: string
	title: string
	type: 'query' | 'chart'
	sort_order: number
}

export type WorkbookQuery = {
	name: string
	title: string
	folder?: string | null
	sort_order: number
	is_native_query?: boolean
	is_script_query?: boolean
	is_builder_query?: boolean
}

export type WorkbookChart = {
	name: string
	title: string
	query: string
	chart_type: ChartType
	folder?: string | null
	sort_order: number
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
	folders: WorkbookFolder[]
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
	sort_order: number
	folder?: string | null
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
	chart_type: ChartType
	sort_order: number
	folder?: string | null
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
	vertical_compact: boolean
	has_workbook_access: boolean
}

export type WorkbookDashboardItem =
	| WorkbookDashboardChart
	| WorkbookDashboardText
	| WorkbookDashboardFilter

/** Where a cell sits: a column, a row, and a span of each. */
export type Placement = {
	x: number
	y: number
	w: number
	h: number
}

/** A placement with the cell it belongs to. What a grid is drawn from. */
export type Layout = Placement & {
	/** The cell's identity, stable across a move. */
	i: string
}

/**
 * The widths a dashboard is laid out for, narrowest first.
 *
 * A key names a layout an author can arrange, not a screen — the grid picks one
 * by its own box, so a dashboard in a narrow desk panel is served the same
 * layout as one on a phone. Another width is another key here, and the table in
 * `grid_placement.ts` that says how wide each one is.
 */
export type BreakpointKey = 'sm' | 'lg'

/**
 * What every dashboard item carries about where it sits.
 *
 * `layout` is the placement at the widest breakpoint, and it is the one every
 * item has — it is what a dashboard authored before there was more than one
 * width already holds, and what a new item is given. `layouts` holds the
 * narrower ones, and only the ones an author actually arranged: a breakpoint an
 * item says nothing about is derived from the next wider one, so a dashboard
 * nobody has laid out for a phone still reads on a phone.
 *
 * Both are read through `placementsFor` and written through `writePlacement`.
 * Nothing else may reach for either field, because those two functions are what
 * knows that the widest breakpoint is stored apart from the rest.
 */
export type WorkbookDashboardItemLayout = {
	layout: Layout
	layouts?: Partial<Record<BreakpointKey, Placement>>
}

export type WorkbookDashboardChart = WorkbookDashboardItemLayout & {
	type: 'chart'
	chart: string
}
export type WorkbookDashboardFilter = WorkbookDashboardItemLayout & {
	type: 'filter'
	filter_name: string
	filter_type: FilterType
	links: Record<string, string>
	default_operator?: FilterOperator
	default_value?: FilterValue
	icon?: string
}
export type WorkbookDashboardText = WorkbookDashboardItemLayout & {
	type: 'text'
	text: string
}

// dashboard filter state, keyed by filter name. Which query a filter lands on is
// the server's business — every surface sends the state and the grid it sits
// on, and the links are read there.
export type ViewerFilters = Record<string, { operator: FilterOperator; value: FilterValue }>

export type ShareAccess = 'view' | 'edit' | undefined
export type WorkbookSharePermission = {
	email: string
	full_name: string
	user_image?: string
	access: ShareAccess
}
