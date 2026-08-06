// A dashboard as a viewer reads it: `insights.api.viewer`, plus the one write a
// reader can make (duplicate, below).
//
// Every read surface asks the server by name and lets it decide what runs — the
// desk island, the public page and the SPA's dashboard page alike. The query
// behind a chart never comes back.

import { call } from 'frappe-ui'
import type { Layout } from '../types/workbook.types'
import type { FilterOperator, FilterType, FilterValue } from '../types/query.types'

export type ViewerDashboardItem = {
	type: 'chart' | 'text' | 'filter'
	layout: Layout
	chart?: string
	text?: string
	filter_name?: string
	filter_type?: FilterType
	// the icon its author picked for it, by lucide name
	icon?: string
	default_operator?: FilterOperator
	default_value?: FilterValue
	// the cards this filter changes. Which column it lands on stays server-side;
	// the names are what the bar needs to refetch the right cards and what lets an
	// empty card say a filter caused it
	charts?: string[]
}

export type ViewerDashboard = {
	name: string
	slug: string
	title: string
	items: ViewerDashboardItem[]
	vertical_compact_layout: boolean
	modified: string
	// what this reader may do with it. The surface offers an action only where the
	// server granted it, so nothing dangles an affordance the server would refuse
	can_edit: boolean
	can_duplicate: boolean
	// where editing happens — the builder is workbook-scoped. Null for anyone who
	// cannot edit
	workbook: string | null
}

// dashboard filter state, keyed by filter name. Which query a filter lands on is
// the server's business — the links that say so never reach a viewer.
export type ViewerFilters = Record<string, { operator: FilterOperator; value: FilterValue }>

export function fetchDashboard(dashboard: string): Promise<ViewerDashboard> {
	return call('insights.api.viewer.get_dashboard', { dashboard })
}

/** The values a filter offers. The column behind it is the server's to know. */
export function fetchFilterValues(
	dashboard: string,
	filter_name: string,
	search_term?: string,
): Promise<string[]> {
	return call('insights.api.viewer.get_filter_values', { dashboard, filter_name, search_term })
}

/** Where a duplicate landed: the workbook it made, and the dashboard inside it. */
export type DuplicatedDashboard = { workbook: string; dashboard: string }

/**
 * Copy a dashboard's closure into a workbook of the caller's own.
 *
 * Shipped content is read-only on a site, so this is the only way to change it.
 * The server decides who may: an authoring seat, and read on the dashboard.
 */
export function duplicateDashboard(dashboard: string): Promise<DuplicatedDashboard> {
	return call('insights.api.bundles.duplicate_dashboard', { dashboard })
}
