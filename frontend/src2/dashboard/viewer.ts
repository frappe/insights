// A dashboard as a viewer reads it: `insights.api.viewer`, plus the one write a
// reader can make (duplicate, below).
//
// Every read surface asks the server by name and lets it decide what runs — the
// desk island, the public page and the SPA's dashboard page alike. The query
// behind a chart never comes back.
//
// This is also where the shape a dashboard page draws itself from lives, because
// reading is the shape and writing is an addition to it. The other feed that
// fills it is `authoring.ts`, which reads the document the builder is editing
// instead. Above the fetch the page is the same either way.

import { call } from 'frappe-ui'
import { markRaw, reactive, type Component } from 'vue'
import type { FilterType } from '../helpers/constants'
import { navigate } from '../helpers/navigation'
import { isFilterApplied } from '../query/components/filter_utils'
import type { FilterOperator, FilterValue } from '../types/query.types'
import type { Layout } from '../types/workbook.types'
import { readFilters, writeFilters } from './filter_storage'
import ViewerItem from './ViewerItem.vue'

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
	// the names are what the page needs to refetch the right cards and what lets
	// an empty card say a filter caused it
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

export type ViewerFilterState = ViewerFilters[string]

/**
 * The state one filter's own defaults describe, or nothing where they describe
 * none. `isFilterApplied` is what decides — an author who defaulted a filter to
 * `is set` set a default, and there is no value to go with it.
 */
export function defaultFilterState(item: ViewerDashboardItem): ViewerFilterState | undefined {
	const operator = item.default_operator
	const value = item.default_value
	if (!isFilterApplied(item.filter_type!, operator, value)) return
	return { operator: operator!, value: value! }
}

/** The state a dashboard's own filter defaults describe. */
export function defaultFilters(items: ViewerDashboardItem[]): ViewerFilters {
	const defaults: ViewerFilters = {}
	items.forEach((item) => {
		if (item.type !== 'filter') return
		const state = defaultFilterState(item)
		if (state) defaults[item.filter_name!] = state
	})
	return defaults
}

/**
 * One grid cell, as the page hands it over.
 *
 * Every feed answers with a component of this shape, and that component is the
 * one place the surfaces still differ: a reader gets a card, an author gets a
 * card they can move, edit and throw away. The page passes the same five props
 * to either and lets it use what it can — a reader's card routes filter state,
 * an author's routes it through links the reader never receives.
 */
export type DashboardCellProps = {
	item: ViewerDashboardItem
	index: number
	// the page this cell sits on. It carries the chart's audience, and it is what
	// lets the server route filter state to the query behind the card
	dashboard: string
	filters?: ViewerFilters
	priority?: number
	refreshToken?: number
}

export type DashboardMenuOption = {
	label: string
	icon: any
	onClick: () => void
}

/**
 * Writing, for whoever holds it. Absent on every read surface, and nothing it
 * carries is drawn without it.
 *
 * It carries components because the builder's editing layer cannot be reached
 * from a read surface at all: it pulls in the workbook's stores and its forms,
 * which an island refuses by weight and by rule. So the feed that has them hands
 * them over, the same way the chart store's authoring feed carries drill-down.
 */
export type DashboardAuthoring = {
	// true while the reader is moving things about
	editing: boolean
	// the edit chrome, drawn in the page's header band
	actions: Component
	// what this capability adds to the page's one menu
	menuOptions: DashboardMenuOption[]
	rename: (title: string) => void
	moveItems: (layouts: Layout[]) => void
	// a chart dragged in from the workbook's sidebar
	dragOver: (event: DragEvent) => void
	drop: (event: DragEvent) => void
}

/**
 * Everything a dashboard page draws itself from.
 *
 * Each capability is present only where it was granted, so a surface never has
 * to ask which surface it is: it draws what the feed carries and nothing else.
 */
export type DashboardSource = {
	loading: boolean
	// a dashboard that is missing and one this reader may not have answer the same
	unavailable: boolean
	name: string
	title: string
	// every cell, in the order the grid lays them out — a filter is one of them,
	// in the position its author gave it
	items: ViewerDashboardItem[]
	// where the filters start on this surface
	filters: ViewerFilters
	// remembering where a reader left them. Absent where the document's own
	// defaults are the answer
	saveFilters?: (filters: ViewerFilters) => void
	verticalCompact: boolean
	cell: Component
	// reaching the builder from here. Absent for a reader who cannot edit — and
	// for the builder, which is already there
	openBuilder?: () => void
	// shipped content is read-only, so a copy is the only way to change it
	duplicate?: {
		run: () => void
		running: boolean
		failed: boolean
	}
	authoring?: DashboardAuthoring
}

/** The read feed: a saved dashboard, named to the server. */
export function useSavedDashboard(dashboard: string): DashboardSource {
	const source = reactive<DashboardSource>({
		loading: true,
		unavailable: false,
		name: '',
		title: '',
		items: [],
		filters: {},
		verticalCompact: true,
		cell: markRaw(ViewerItem),
	})

	// A dashboard that is missing and one the viewer may not read answer the same,
	// so there is one page state for both.
	fetchDashboard(dashboard)
		.then((doc) => {
			source.name = doc.name
			source.title = doc.title
			source.items = doc.items
			source.verticalCompact = doc.vertical_compact_layout
			// a reader comes back to the filters they left, over the defaults the
			// author set. Nothing on the server holds per-user view state
			source.filters = { ...defaultFilters(doc.items), ...readFilters(doc.name) }
			source.saveFilters = (filters) => writeFilters(doc.name, filters)
			if (doc.can_edit && doc.workbook) {
				const workbook = doc.workbook
				source.openBuilder = () => navigate(`/workbook/${workbook}/dashboard/${doc.name}`)
			}
			if (doc.can_duplicate) {
				source.duplicate = duplicateCapability(doc.name)
			}
		})
		.catch(() => (source.unavailable = true))
		.finally(() => (source.loading = false))

	return source
}

/**
 * The copy is the caller's own document in a workbook of their own, so it lands
 * in the builder rather than here. Copying a closure is a handful of inserts,
 * but it is a round trip either way: the page says so while it runs, and says so
 * if it failed — the menu is closed by then and there is nowhere else for the
 * answer to go.
 */
function duplicateCapability(dashboard: string) {
	const capability = reactive({
		running: false,
		failed: false,
		run: async () => {
			if (capability.running) return
			capability.running = true
			capability.failed = false
			try {
				const copy = await duplicateDashboard(dashboard)
				navigate(`/workbook/${copy.workbook}/dashboard/${copy.dashboard}`)
			} catch (error) {
				capability.failed = true
			} finally {
				capability.running = false
			}
		},
	})
	return capability
}

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
