// A dashboard as a reader gets it: `insights.api.view`, and nothing else.
//
// Every view surface asks the server by name and lets it decide what runs — the
// desk island, the public page and the SPA's dashboard page alike. The query
// behind a chart never comes back.
//
// The `DashboardView` a page draws itself from lives here too, because reading
// is the shape and writing is an addition to it. `builder.ts` builds the same
// shape from the document the builder is editing. Above the fetch the page is
// the same either way.

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
	type ChartReadSurface,
	type DashboardFilterContext,
} from '../charts/chart_view'
import {
	FILTER_TYPE_KINDS,
	operatorOf,
	type Filter,
} from '../components/filter_picker/filter_picker'
import type { FilterType } from '../helpers/constants'
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
	// which reading of a Number chart this cell draws, by id
	reading?: string
	text?: string
	filter_name?: string
	filter_type?: FilterType
	// the icon its owner picked for it, by lucide name
	icon?: string
	default_operator?: FilterOperator
	default_value?: FilterValue
	// the cards this filter changes. Which column it lands on stays server-side;
	// the names are what narrows a request to the cards a filter reaches and what
	// lets an empty card say a filter caused it
	charts?: string[]
}

export type DashboardViewDoc = {
	name: string
	title: string
	items: DashboardViewItem[]
	// every chart the grid names, as the card frames read them
	charts: ChartViewDoc[]
	vertical_compact_layout: boolean
	// what this reader may do with it. The surface offers an action only where the
	// server granted it, so nothing dangles an affordance the server would refuse
	can_write: boolean
	// where editing happens — the builder is workbook-scoped. Null for anyone who
	// cannot edit
	workbook: string | null
}

export type FilterState = FilterValues[string]

/** What a filter's own defaults are read off: the cell as either source holds it. */
type FilterDefaults = {
	type: string
	filter_name?: string
	filter_type?: FilterType
	default_operator?: FilterOperator
	default_value?: FilterValue
}

/**
 * What every filter on a dashboard opens on, as its owner set it.
 *
 * Whether a default says enough to run is the operator's answer, not the
 * value's — `is_set` asks about the column itself and carries no value, which is
 * the same rule the server states in `_filter_is_set`.
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
 * Call `apply` when a filter's default moves.
 *
 * Not when the item carrying it is replaced by one that says the same: Refresh
 * hands every filter cell a new item, and applying the default then would
 * overwrite the reader's own choice and store the default as that choice.
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
 * The filter cell, measured from the CSS that draws it the way `numberCardRows`
 * measures a card: the trigger plus the cell's own padding.
 */
const FILTER = {
	/** The trigger is frappe-ui's `sm` Button, `h-7`. */
	trigger: 28,
	/** A dashboard cell's `p-2`, top and bottom. */
	cellPadding: 2 * 8,
}

/** Rows a filter cell takes. */
export const FILTER_ROWS = Math.ceil((FILTER.trigger + FILTER.cellPadding) / ROW_HEIGHT)

/**
 * What the grid is told about a cell beyond its stored layout.
 *
 * A Number cell's height is what the card of the reading it names holds, so the
 * owner sets the width and the height follows the config — including after the
 * config changes. And two of them fit one narrow row, where every other cell
 * takes the row to itself. A filter cell is its trigger, which is one height and
 * never anything else. It keeps its row, so no card fills the space beside the
 * filters.
 *
 * Nothing is written back. Both sources derive it on every read from whichever
 * chart frames they hold, so a chart edited elsewhere needs no layout save to be
 * drawn at its new height.
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
 * One grid cell, as the body hands it over.
 *
 * A surface picks the cell it mounts `DashboardBody` with, and every one of them
 * takes this shape. The body passes the same props to any of them and lets each
 * use what it can.
 */
export type DashboardCellProps = {
	// the page this cell sits on. Everything a cell reads or changes — the card's
	// rows, the filter state, the values a filter offers — it asks the page for
	dashboard: DashboardView
	item: DashboardViewItem
	index: number
}

/**
 * One thing a reader may do with the dashboard in front of them.
 *
 * An action either runs here or leads somewhere, never both — a surface that
 * can draw a link draws one, and the rest click it. `icon` is the bare lucide
 * name; each surface spells it the way its own icons are named.
 *
 * This is the shape the desk island reports too, so a host outside Insights
 * draws its own chrome from the same list.
 */
export type DashboardAction = { label: string; icon?: string } & (
	| { onClick: () => void }
	| { href: string }
)

/**
 * Writing, for whoever holds it. Absent on every view surface.
 *
 * The edit chrome is not here. The builder draws its own header and reaches
 * `DashboardEditActions` by import.
 */
export type DashboardBuilderActions = {
	// true while the reader is moving things about
	editing: boolean
	// what this capability adds to the dashboard's actions
	menuOptions: DashboardAction[]
	/** The breakpoint being arranged. What the grid is drawn and dragged at. */
	arranging: BreakpointKey
	// `before` is the grid the gesture started from, which is what a moved cell
	// is measured against
	moveItems: (key: BreakpointKey, layouts: Layout[], before: Layout[]) => void
	// a chart dragged in from the workbook's sidebar
	dragOver: (event: DragEvent) => void
	drop: (event: DragEvent) => void
}

/**
 * A dashboard as a page holds it: what the document is, what this reader may do
 * with it, and the reads behind its cards.
 *
 * Each capability is present only where the server granted it. A surface draws
 * what is there and never asks which surface it is.
 *
 * How it is drawn is not here. `DashboardBody` takes the grid and the cell as
 * props of its own, from whichever surface mounts it.
 */
export type DashboardView = {
	loading: boolean
	// a dashboard that is missing and one this reader may not have answer the same
	notFound: boolean
	name: string
	title: string
	// every cell, in the order the grid lays them out — a filter is one of them,
	// in the position its owner gave it
	items: DashboardViewItem[]
	cellRules: CellRules
	verticalCompact: boolean
	// where the filters stand, keyed by filter name
	filters: FilterValues
	setFilter: (filter_name: string, state?: FilterState) => void
	// the values a filter offers, narrowed by what the rest of the grid holds
	filterValues: (filter_name: string, search_term?: string) => Promise<string[]>
	// the bounds a number filter's presets are cut from, narrowed the same way
	filterRange: (filter_name: string) => Promise<[number, number] | undefined>
	// what the reader narrowed each card to, on the columns the card draws
	cardFilters: Record<string, Filter[]>
	setCardFilters: (chart: string, filters: Filter[]) => void
	// the values and the bounds a card filter offers, read off what the card draws
	cardValues: (chart: string, column: string, search_term?: string) => Promise<string[]>
	cardRange: (chart: string, column: string) => Promise<[number, number] | undefined>
	// whether something the reader can undo narrows this card — a grid filter
	// that reaches it, or the filter they put on the card — so an empty one can
	// say why
	filtered: (chart: string) => boolean
	// take off everything `filtered` counts
	resetCardFilters: (chart: string) => void
	// The card's rows, by chart and not by cell: several cells can draw one chart
	// — a Number chart is one cell per reading — and the read behind them is one.
	chartView: (chart: string) => ChartRead | undefined
	// A cell that draws a chart asks for its rows when it mounts. A read whose
	// question has not changed drops the load, and one that went stale runs it.
	loadChart: (chart: string) => void
	// read the dashboard again, and every card on it with it
	refresh: (force?: boolean) => void
	// where the builder for this dashboard is, as an SPA route. Absent for a
	// reader who cannot edit — and for the builder, which is already there.
	// Nothing navigates here; a surface resolves it the way its own links resolve
	builderRoute?: string
	// where a chart on this dashboard is edited, as an SPA route. Absent for a
	// reader who cannot edit it
	chartRoute?: (chart: string) => string | undefined
	builder?: DashboardBuilderActions
}

/** The same dashboard, from the one surface that always holds the writing half. */
export type DashboardInBuilder = DashboardView & { builder: DashboardBuilderActions }

/** One dashboard's page, and the way a mount opens it. */
type DashboardPage = {
	view: DashboardView
	open: () => void
	// the next mount reads the dashboard and its cards again, not the snapshot
	// this page holds
	forget: () => void
}

/**
 * Every page this tab has opened, by the surface and the reference naming it.
 *
 * A page outlives the component that first asked for it. The reads its cards
 * draw from are cached under the page's own surface id, and they close over the
 * filters this page holds — so a second page under that id would leave every
 * card reading a state nobody is looking at. One page per id is what keeps the
 * two the same thing.
 */
const pages = new Map<string, DashboardPage>()

function pageFor(reference: string, surface: DashboardSurface): DashboardPage {
	const key = `${surface}:${reference}`
	const existing = pages.get(key)
	if (existing) return existing

	// A page is always first asked for inside a component's `setup` and outlives
	// it. Its computeds would stop with that component, leaving a page that reads
	// whatever it last held. Detached, they live as long as the page does.
	const scope = effectScope(true)
	const page = scope.run(() => makeDashboardPage(key, reference, surface)) as DashboardPage
	pages.set(key, page)
	return page
}

/**
 * Drop a dashboard's snapshot from every page that holds it.
 *
 * A page is drawn as the reader left it until Refresh. The author's own save is
 * the exception: they are the one reader who knows the dashboard moved, so the
 * next mount of it in this tab reads it again.
 */
export function invalidateDashboard(name: string) {
	pages.forEach((page) => {
		if (page.view.name === name) page.forget()
	})
}

/**
 * A saved dashboard, named to the server.
 *
 * The reference is read reactively, because a surface can outlive the dashboard
 * it was mounted for. The desk island keeps one Vue app across a route change
 * and hands down the next reference as a prop, and the SPA's dashboard route
 * reuses its component when only the parameter moves. Both would otherwise sit
 * on the first dashboard they fetched.
 *
 * What a mount gets is a view of the page, never a page of its own: opening one
 * dashboard twice — a visit, the list, the same visit again — is two mounts of
 * one page, and the filters the second one moves are the filters the cards read.
 */
export function useDashboardView(
	reference: MaybeRefOrGetter<string>,
	// which page the view is on, for the `dashboard_viewed` event
	surface: DashboardSurface,
): DashboardView {
	const page = () => pageFor(toValue(reference), surface)

	// A page the tab already opened is drawn as the reader left it: the
	// dashboard and every card on it are one snapshot, and only Refresh or a
	// reload replaces it.
	watch(
		() => toValue(reference),
		() => page().open(),
		{ immediate: true },
	)

	// Read off the page rather than listed again here, which would be a second
	// statement of `DashboardView` — and one that would go stale as the type
	// grows. A member is answered by whichever page the reference names now.
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
		name: '',
		title: '',
		items: [] as DashboardViewItem[],
		verticalCompact: true,
		filters: {} as FilterValues,
		cardFilters: {} as Record<string, Filter[]>,
		// where the builder for this dashboard is, for a reader who may edit it
		builderRoute: undefined as string | undefined,
		// the workbook a reader who may edit is sent to, for a chart on the grid
		workbook: undefined as string | undefined,
	})

	// one read per chart, so the cells that draw one chart ask once. Reactive,
	// because a cell's height is read off the chart its card draws
	const reads = shallowReactive(new Map<string, ChartRead>())

	// The one surface object this page reads through, which is what the read
	// cache files its reads under. It carries the page's own filters, so every
	// mount of this page draws the rows the filters in front of the reader name.
	const viewSurface: ChartReadSurface = {
		id: `view:${key}`,
		filterContext: filterContextFor,
	}

	// Which fetch the page is waiting for. Two can land out of order, and the
	// older one would draw a dashboard the newer one replaced.
	let fetches = 0
	// whether a dashboard answer has landed, so a mount has something to draw
	let opened = false
	let pending = false

	/** Only the filters that reach this card. The rest leave its request alone. */
	function filtersFor(chart: string): FilterValues {
		const reaching: FilterValues = {}
		state.items.forEach((item) => {
			if (item.type !== 'filter' || !item.charts?.includes(chart)) return
			const filter = state.filters[item.filter_name!]
			if (filter) reaching[item.filter_name!] = filter
		})
		return reaching
	}

	// The chart runs once for every cell that draws it, so it is the cell that
	// reads first that says when — the topmost, leftmost one.
	function priorityFor(chart: string) {
		const ranks = state.items
			.filter((item) => item.type === 'chart' && item.chart === chart)
			.map((item) => layoutRank(item.layout))
		return ranks.length ? Math.min(...ranks) : undefined
	}

	// A card filter is the reader's own, on a column the card draws, so it
	// travels as itself and lands on the card's own query server-side.
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
	 * Open a read for every chart the grid names, and run them.
	 *
	 * Once the layout has landed, rather than when a cell first asks: the cells
	 * are drawn from these, and a read opened mid-render would put a card through
	 * its loading state during the render that mounted it.
	 */
	function openReads(charts: ChartViewDoc[], force: boolean) {
		const named = new Set(charts.map((doc) => doc.name))
		;[...reads.keys()].forEach((chart) => named.has(chart) || reads.delete(chart))
		// the rows a view draws are narrowed by the filters it holds, so its reads
		// belong to it: the same chart on another dashboard reads its own. The
		// frame is a placeholder for a read that drew nothing yet; a read that did
		// takes the new one with its rows.
		charts.forEach((doc) => {
			const read = useChartView(doc.name, viewSurface, doc)
			read.executionPriority = priorityFor(doc.name)
			reads.set(doc.name, read)
			read.load(force)
		})
	}

	// Every card asks again, and each one drops its own load where the question
	// has not changed — so moving one filter re-runs the cards it reaches and
	// leaves the rest of the page alone without anything here routing it.
	function rerun() {
		reads.forEach((read) => read.load())
	}

	function setFilter(filter_name: string, filter?: FilterState) {
		const moved = { ...state.filters }
		if (filter) moved[filter_name] = filter
		else delete moved[filter_name]
		state.filters = moved
		// a reader comes back to the filters they left; nothing on the server
		// holds per-user view state
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
		// a grid filter reaches other cards too, and each drops its own load where
		// its question has not changed
		rerun()
	}

	function open() {
		if (opened || pending) return
		fetch(false)
	}

	function refresh(force = false) {
		fetch(force)
	}

	// A dashboard that is missing and one the reader may not read answer the
	// same, so there is one page state for both.
	function fetch(force: boolean) {
		const token = ++fetches
		pending = true
		state.loading = !opened
		fetchDashboard(reference, surface)
			.then((doc) => {
				if (token !== fetches) return
				opened = true
				state.notFound = false
				state.name = doc.name
				state.title = doc.title
				state.items = doc.items
				state.verticalCompact = doc.vertical_compact_layout
				// what the reader last chose wins over the defaults the owner set
				state.filters = { ...defaultFilterStates(doc.items), ...readFilters(doc.name) }
				const editable = doc.can_write && doc.workbook
				state.builderRoute = editable
					? `/workbook/${doc.workbook}/dashboard/${doc.name}`
					: undefined
				state.workbook = editable ? doc.workbook! : undefined
				openReads(doc.charts, force)
			})
			.catch(() => {
				if (token !== fetches) return
				opened = false
				state.notFound = true
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
		name: computed(() => state.name),
		title: computed(() => state.title),
		items: computed(() => state.items),
		// read off the chart each card draws, so a cell is as tall as its picture
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
	}) as DashboardView

	return {
		view,
		open,
		forget: () => {
			opened = false
			// the cards are the snapshot too, and a re-pointed filter link leaves
			// their request as it was
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
 * The values a filter offers. The column behind it is the server's to know.
 *
 * `filters` is the other filters' current state. The server routes it and leaves
 * this filter out of its own list, so the offer narrows to what the rest of the
 * grid currently holds.
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
