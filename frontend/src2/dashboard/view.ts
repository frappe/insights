// A dashboard as a reader gets it, through `insights.api.view` only.
//
// The client names the dashboard and the server decides what runs. This holds
// for the desk island, the public page and the SPA's dashboard page. The query
// behind a chart never reaches the client.
//
// `DashboardView` lives here too, because writing only adds to the read shape.
// `builder.ts` builds the same shape from the document the builder edits.

import { call } from 'frappe-ui'
import {
	computed,
	effectScope,
	reactive,
	shallowReactive,
	toValue,
	watch,
	type MaybeRefOrGetter,
} from 'vue'
import { numberCardRows } from '../charts/adapter/number'
import {
	useChartView,
	type ChartRead,
	type ChartViewDoc,
	type ChartReadContext,
	type DashboardFilterContext,
} from '../charts/chart_view'
import {
	FILTER_TYPE_KINDS,
	operatorOf,
	type Filter,
} from '../components/filter_picker/filter_picker'
import { showErrorToast } from '../helpers'
import type { FilterType } from '../helpers/constants'
import { navigate } from '../helpers/navigation'
import { stableStringify } from '../helpers/stable_stringify'
import type { NumberChartConfig } from '../types/chart.types'
import type { FilterOperator, FilterValue } from '../types/query.types'
import type {
	BreakpointKey,
	FilterValues,
	Layout,
	WorkbookDashboardItemLayout,
} from '../types/workbook.types'
import { readFilters, writeFilters } from './filter_storage'
import { layoutRank, ROW_HEIGHT, type CellRules } from './grid_placement'

export type DashboardViewItem = WorkbookDashboardItemLayout & {
	type: 'chart' | 'text' | 'filter'
	chart?: string
	// the id of the Number chart reading this cell shows
	reading?: string
	text?: string
	filter_name?: string
	filter_type?: FilterType
	// a lucide icon name
	icon?: string
	default_operator?: FilterOperator
	default_value?: FilterValue
	// the charts this filter applies to. Only the server knows which column it
	// filters. The client uses the names to send the filter only to these charts,
	// and to let an empty card say that a filter emptied it
	charts?: string[]
}

export type DashboardViewDoc = {
	name: string
	title: string
	items: DashboardViewItem[]
	charts: ChartViewDoc[]
	vertical_compact_layout: boolean
	// the page shows an action only when the server allows it, so no action fails
	// when clicked
	can_write: boolean
	// the reader may not edit the dashboard, but may duplicate its workbook
	can_copy: boolean
	// the workbook to edit in or to duplicate. Null when the reader may do neither
	workbook: string | null
}

export type FilterState = FilterValues[string]

/** A filter cell's defaults, as both the view and the builder store them. */
type FilterDefaults = {
	type: string
	filter_name?: string
	filter_type?: FilterType
	default_operator?: FilterOperator
	default_value?: FilterValue
}

/**
 * The state each filter opens with, from the defaults its owner set.
 *
 * The operator decides whether a default needs a value. `is_set` needs none.
 * The server applies the same rule in `_filter_is_set`.
 */
export function defaultFilterStates(items: FilterDefaults[]): FilterValues {
	const states: FilterValues = {}
	items.forEach((item) => {
		if (item.type != 'filter' || !item.filter_name || !item.filter_type) return

		const operator = item.default_operator
		if (!operator) return
		const kind = FILTER_TYPE_KINDS[item.filter_type]
		const needsValue = operatorOf(kind, operator)?.needsValue ?? true
		if (needsValue && !item.default_value) return

		states[item.filter_name] = { operator, value: item.default_value }
	})
	return states
}

/**
 * Call `apply` when a filter's default changes.
 *
 * Do not call it when Refresh replaces the item with an equal one. Applying the
 * default then would overwrite the reader's choice and store the default as
 * that choice.
 */
export function watchFilterDefault(
	item: () => FilterDefaults,
	apply: (operator: FilterOperator, value: FilterValue) => void,
) {
	return watch(
		() => stableStringify([item().default_operator, item().default_value]),
		() => {
			const { default_operator, default_value } = item()
			if (default_operator != null && default_value != null)
				apply(default_operator, default_value)
		},
	)
}

/**
 * The filter cell's size, measured from its CSS, as `numberCardRows` does for a
 * card.
 */
const FILTER = {
	/** frappe-ui's `sm` Button, `h-7`. */
	trigger: 28,
	/** The cell's `p-2`, top and bottom. */
	cellPadding: 2 * 8,
}

export const FILTER_ROWS = Math.ceil((FILTER.trigger + FILTER.cellPadding) / ROW_HEIGHT)

/**
 * Grid rules for each cell, beyond its stored layout.
 *
 * A Number cell's height follows the card of its reading. The owner sets only
 * the width, and the height follows later config changes. Two Number cells fit
 * in one narrow row; every other cell takes a full row. A filter cell has one
 * fixed height and takes its row alone, so no card fills the space beside the
 * filters.
 *
 * The rules are not saved. The view and the builder derive them on each read
 * from the charts they hold. So a chart edited elsewhere shows at its new height
 * without a layout save.
 */
export function cellRulesFor(
	items: DashboardViewItem[],
	chartFor: (chart: string) => { chart_type?: string; config?: object } | undefined | null,
): CellRules {
	const rules: CellRules = {}
	for (const item of items) {
		if (item.type === 'filter') {
			rules[item.layout.i] = { height: FILTER_ROWS, exclusiveRow: true }
			continue
		}
		if (item.type !== 'chart' || !item.chart) continue
		const chart = chartFor(item.chart)
		if (chart?.chart_type !== 'Number') continue
		rules[item.layout.i] = {
			height: numberCardRows(chart.config as NumberChartConfig, item.reading),
			halfWidth: true,
		}
	}
	return rules
}

/**
 * The props of one grid cell.
 *
 * Each page passes its own cell component to `DashboardBody`. The body passes
 * these same props to every cell component, and each one uses what it needs.
 */
export type DashboardCellProps = {
	dashboard: DashboardView
	item: DashboardViewItem
	index: number
}

/**
 * One action a reader may take on the dashboard.
 *
 * An action has either `onClick` or `href`, never both. A page that can render
 * a link renders `href` as one; other pages navigate on click. `icon` is the
 * bare lucide name, and each page formats it for its own icon set.
 *
 * The desk island reports the same shape, so a host outside Insights renders
 * its own header from this list.
 */
export type DashboardAction = { label: string; icon?: string } & (
	| { onClick: () => void }
	| { href: string }
)

/**
 * Edit actions. Only the builder has them.
 *
 * The edit header is not here. The builder renders its own header and imports
 * `DashboardEditActions`.
 */
export type DashboardBuilderActions = {
	editing: boolean
	menuOptions: DashboardAction[]
	/** The breakpoint the grid is rendered and dragged at. */
	arranging: BreakpointKey
	// `before` is the layout when the drag started. A moved cell is measured
	// against it
	moveItems: (key: BreakpointKey, layouts: Layout[], before: Layout[]) => void
	// a chart dragged in from the workbook's sidebar
	dragOver: (event: DragEvent) => void
	drop: (event: DragEvent) => void
}

/**
 * A dashboard as a page holds it: the document, what the reader may do with
 * it, and the reads behind its cards.
 *
 * Each capability is present only when the server allows it. A page renders
 * what is there and never checks which page it is.
 *
 * Rendering is not here. `DashboardBody` gets the grid and the cell component
 * as props from the page that mounts it.
 */
export type DashboardView = {
	loading: boolean
	// the dashboard is missing, or the reader may not read it. Both are Not Found
	notFound: boolean
	// the request failed for another reason, so a retry may succeed
	failed: boolean
	name: string
	title: string
	// every cell in grid order, filters included
	items: DashboardViewItem[]
	cellRules: CellRules
	verticalCompact: boolean
	// filter state, keyed by filter name
	filters: FilterValues
	setFilter: (filter_name: string, state?: FilterState) => void
	// a filter's values, narrowed by the other filters
	filterValues: (filter_name: string, search_term?: string) => Promise<string[]>
	// the min and max for a number filter's presets, narrowed the same way
	filterRange: (filter_name: string) => Promise<[number, number] | undefined>
	// the filters the reader put on each card
	cardFilters: Record<string, Filter[]>
	setCardFilters: (chart: string, filters: Filter[]) => void
	cardValues: (chart: string, column: string, search_term?: string) => Promise<string[]>
	cardRange: (chart: string, column: string) => Promise<[number, number] | undefined>
	// whether a dashboard filter or a card filter narrows this card, so an empty
	// card can say why
	filtered: (chart: string) => boolean
	// clear every filter that `filtered` counts
	resetCardFilters: (chart: string) => void
	// Keyed by chart, not by cell. Several cells can show one chart (a Number
	// chart has one cell per reading), and they share one read.
	chartView: (chart: string) => ChartRead | undefined
	// A chart cell calls this when it mounts. The read skips the load if its
	// request is unchanged, and runs it if the read is stale.
	loadChart: (chart: string) => void
	// reload the dashboard and all its cards
	refresh: (force?: boolean) => void
	// the SPA route of this dashboard's builder. Absent when the reader may not
	// edit, and in the builder itself. Each page resolves it the way its own
	// links resolve
	builderRoute?: string
	// the SPA route where a chart is edited. Absent when the reader may not edit it
	chartRoute?: (chart: string) => string | undefined
	// copy the dashboard's workbook and open the copy. Absent when the reader may
	// not copy it
	duplicate?: () => void
	builder?: DashboardBuilderActions
}

/** A `DashboardView` in the builder, where `builder` is always present. */
export type DashboardInBuilder = DashboardView & { builder: DashboardBuilderActions }

type DashboardPage = {
	view: DashboardView
	open: () => void
	// the next mount reloads the dashboard and its cards instead of using this
	// snapshot
	forget: () => void
}

/**
 * Every dashboard page this tab has opened, keyed by `surface` and reference.
 *
 * A page outlives the component that first asked for it. Its card reads are
 * cached under the page's id, and they use this page's filters. A second page
 * under the same id would leave the cards reading filters that nobody sees. So
 * there is one page per id.
 */
const pages = new Map<string, DashboardPage>()

function pageFor(reference: string, surface: DashboardSurface): DashboardPage {
	const key = `${surface}:${reference}`
	const existing = pages.get(key)
	if (existing) return existing

	// A page is first created inside a component's `setup`, but outlives it. Its
	// computeds would stop with that component, and the page would keep stale
	// values. A detached scope keeps them alive as long as the page.
	const scope = effectScope(true)
	const page = scope.run(() => makeDashboardPage(key, reference, surface)) as DashboardPage
	pages.set(key, page)
	return page
}

/**
 * Drop a dashboard's snapshot from every page that holds it.
 *
 * A page keeps what the reader last saw until Refresh. The author's own save is
 * the exception. The author knows the dashboard changed, so the next mount in
 * this tab reloads it.
 */
export function invalidateDashboard(name: string) {
	pages.forEach((page) => {
		if (page.view.name === name) page.forget()
	})
}

/**
 * A saved dashboard, fetched by reference.
 *
 * The reference is reactive because a page can outlive the dashboard it was
 * mounted for. The desk island keeps one Vue app across a route change and
 * passes the next reference as a prop. The SPA's dashboard route reuses its
 * component when only the parameter changes. Without this, both would keep
 * showing the first dashboard they fetched.
 *
 * Each mount gets a proxy to the shared page, not a page of its own. Opening one
 * dashboard twice is two mounts of one page. So the filters that the second
 * mount changes are the filters that the cards read.
 */
export function useDashboardView(
	reference: MaybeRefOrGetter<string>,
	// which page the view is on, for the `dashboard_viewed` event
	surface: DashboardSurface,
): DashboardView {
	const page = () => pageFor(toValue(reference), surface)

	// A page already opened in this tab shows what the reader left. Only Refresh
	// or a reload replaces it.
	watch(
		() => toValue(reference),
		() => page().open(),
		{ immediate: true },
	)

	// Copy the page's members instead of listing them again here, so this cannot
	// drift from `DashboardView`. Each getter reads the page that the reference
	// names now.
	const view = {}
	for (const member of Object.keys(page().view)) {
		Object.defineProperty(view, member, {
			enumerable: true,
			get: () => page().view[member as keyof DashboardView],
		})
	}
	return view as DashboardView
}

function makeDashboardPage(
	key: string,
	reference: string,
	surface: DashboardSurface,
): DashboardPage {
	const state = reactive({
		loading: true,
		notFound: false,
		failed: false,
		name: '',
		title: '',
		items: [] as DashboardViewItem[],
		verticalCompact: true,
		filters: {} as FilterValues,
		cardFilters: {} as Record<string, Filter[]>,
		builderRoute: undefined as string | undefined,
		// set only when the reader may edit. Chart routes use it
		workbook: undefined as string | undefined,
		// the workbook to duplicate, when the reader may
		copyable: undefined as string | undefined,
	})

	// One read per chart, shared by its cells. Reactive, because a cell's height
	// depends on its chart.
	const reads = shallowReactive(new Map<string, ChartRead>())

	// The read cache keys this page's reads by this id. It includes the page's own
	// filters, so every mount shows the rows for the filters the reader sees.
	const readContext: ChartReadContext = {
		id: `view:${key}`,
		filterContext: filterContextFor,
	}

	// Counts fetches. Two can land out of order, and the older one would replace
	// the newer dashboard.
	let fetches = 0
	// whether a fetch has succeeded, so a mount has something to show
	let opened = false
	let pending = false

	// Only the dashboard filters that apply to this chart, so the other filters
	// leave its request unchanged.
	function filtersFor(chart: string): FilterValues {
		const reaching: FilterValues = {}
		state.items.forEach((item) => {
			if (item.type !== 'filter' || !item.charts?.includes(chart)) return
			const filter = state.filters[item.filter_name!]
			if (filter) reaching[item.filter_name!] = filter
		})
		return reaching
	}

	// A chart runs once for all its cells, so its priority is its first cell's:
	// the topmost, leftmost one.
	function priorityFor(chart: string) {
		const ranks = state.items
			.filter((item) => item.type === 'chart' && item.chart === chart)
			.map((item) => layoutRank(item.layout))
		return ranks.length ? Math.min(...ranks) : undefined
	}

	// Card filters are sent as they are. The server applies them to the card's own
	// query.
	function filterContextFor(chart: string): DashboardFilterContext {
		return {
			chart,
			dashboard: state.name,
			filters: filtersFor(chart),
			cardFilters: (state.cardFilters[chart] || []).map((filter) => ({
				column: filter.column.name,
				operator: filter.operator,
				value: filter.value,
			})),
		}
	}

	/**
	 * Open and run a read for every chart the grid names.
	 *
	 * This runs when the layout lands, not when a cell first asks. Cells render
	 * from these reads. A read opened during a render would put a card through its
	 * loading state in the same render that mounted it.
	 */
	function openReads(charts: ChartViewDoc[], force: boolean) {
		const named = new Set(charts.map((doc) => doc.name))
		;[...reads.keys()].forEach((chart) => named.has(chart) || reads.delete(chart))
		// The reads belong to this page, because its filters narrow their rows. The
		// same chart on another dashboard has its own read. `doc` is only a
		// placeholder for a read with no rows yet. A read that has rows gets the new
		// definition with its next rows.
		charts.forEach((doc) => {
			const read = useChartView(doc.name, readContext, doc)
			read.executionPriority = priorityFor(doc.name)
			reads.set(doc.name, read)
			read.load(force)
		})
	}

	// Every read reloads, and each one skips the load if its request is
	// unchanged. So a filter change reruns only the cards it applies to.
	function rerun() {
		reads.forEach((read) => read.load())
	}

	function setFilter(filter_name: string, filter?: FilterState) {
		const moved = { ...state.filters }
		if (filter) moved[filter_name] = filter
		else delete moved[filter_name]
		state.filters = moved
		// the reader gets back the filters they left. The server stores no
		// per-user view state
		writeFilters(state.name, moved)
		rerun()
	}

	function setCardFilters(chart: string, filters: Filter[]) {
		state.cardFilters = { ...state.cardFilters, [chart]: filters }
		reads.get(chart)?.load()
	}

	function filtered(chart: string) {
		return Boolean(Object.keys(filtersFor(chart)).length || state.cardFilters[chart]?.length)
	}

	function resetCardFilters(chart: string) {
		const reaching = Object.keys(filtersFor(chart))
		const kept = { ...state.filters }
		reaching.forEach((filter_name) => delete kept[filter_name])
		const { [chart]: _, ...cardFilters } = state.cardFilters
		state.filters = kept
		state.cardFilters = cardFilters
		writeFilters(state.name, kept)
		// a dashboard filter applies to other cards too. Each one skips its load if
		// its request is unchanged
		rerun()
	}

	function open() {
		if (opened || pending) return
		fetch(false)
	}

	function refresh(force = false) {
		fetch(force)
	}

	function fetch(force: boolean) {
		const token = ++fetches
		pending = true
		state.loading = !opened
		fetchDashboard(reference, surface)
			.then((doc) => {
				if (token !== fetches) return
				opened = true
				state.notFound = false
				state.failed = false
				state.name = doc.name
				state.title = doc.title
				state.items = doc.items
				state.verticalCompact = doc.vertical_compact_layout
				// the reader's last choice overrides the owner's defaults
				state.filters = { ...defaultFilterStates(doc.items), ...readFilters(doc.name) }
				const editable = doc.can_write && doc.workbook
				state.builderRoute = editable
					? `/workbook/${doc.workbook}/dashboard/${doc.name}`
					: undefined
				state.workbook = editable ? doc.workbook! : undefined
				state.copyable = doc.can_copy && doc.workbook ? doc.workbook : undefined
				openReads(doc.charts, force)
			})
			.catch((error) => {
				if (token !== fetches) return
				opened = false
				state.notFound = error?.exc_type === 'DoesNotExistError'
				state.failed = !state.notFound
			})
			.finally(() => {
				if (token !== fetches) return
				pending = false
				state.loading = false
			})
	}

	const view = reactive({
		loading: computed(() => state.loading),
		notFound: computed(() => state.notFound),
		failed: computed(() => state.failed),
		name: computed(() => state.name),
		title: computed(() => state.title),
		items: computed(() => state.items),
		cellRules: computed<CellRules>(() =>
			cellRulesFor(state.items, (chart) => reads.get(chart)?.doc),
		),
		verticalCompact: computed(() => state.verticalCompact),
		filters: computed(() => state.filters),
		setFilter,
		filterValues: (filter_name: string, search_term?: string) =>
			fetchFilterValues(state.name, filter_name, search_term, state.filters),
		filterRange: (filter_name: string) =>
			call('insights.api.view.get_filter_range', {
				dashboard: state.name,
				filter_name,
				filters: state.filters,
			}),
		cardFilters: computed(() => state.cardFilters),
		setCardFilters,
		cardValues: (chart: string, column: string, search_term?: string) =>
			call('insights.api.view.get_card_values', {
				dashboard: state.name,
				chart,
				column,
				search_term,
			}),
		cardRange: (chart: string, column: string) =>
			call('insights.api.view.get_card_range', { dashboard: state.name, chart, column }),
		filtered,
		resetCardFilters,
		chartView: (chart: string) => reads.get(chart),
		loadChart: (chart: string) => reads.get(chart)?.load(),
		refresh,
		builderRoute: computed(() => state.builderRoute),
		chartRoute: (chart: string) =>
			state.workbook ? `/workbook/${state.workbook}/chart/${chart}` : undefined,
		duplicate: computed(() => {
			const workbook = state.copyable
			if (!workbook) return undefined
			return () => duplicateWorkbook(workbook)
		}),
	}) as DashboardView

	return {
		view,
		open,
		forget: () => {
			opened = false
			// The cards are part of the snapshot. Mark them stale, because a filter
			// linked to other charts can leave a card's request unchanged, and the
			// card would skip its reload.
			reads.forEach((read) => (read.stale = true))
		},
	}
}

/** Which page a dashboard is viewed on, as the `dashboard_viewed` event names it. */
export type DashboardSurface = 'dashboards' | 'shared' | 'desk'

function fetchDashboard(dashboard: string, surface: DashboardSurface): Promise<DashboardViewDoc> {
	return call('insights.api.view.get_dashboard', { dashboard, surface })
}

/**
 * The values a filter lists. Only the server knows the column behind it.
 *
 * `filters` is the current state of the other filters. The server applies them
 * and leaves this filter out, so the list narrows to what the other filters
 * allow.
 */
function fetchFilterValues(
	dashboard: string,
	filter_name: string,
	search_term?: string,
	filters?: FilterValues,
): Promise<string[]> {
	return call('insights.api.view.get_filter_values', {
		dashboard,
		filter_name,
		search_term,
		filters,
	})
}

function duplicateWorkbook(workbook: string) {
	return call('run_doc_method', { dt: 'Insights Workbook', dn: workbook, method: 'duplicate' })
		.then((copy) => navigate(`/workbook/${copy}`))
		.catch((err) => showErrorToast(err, false))
}
