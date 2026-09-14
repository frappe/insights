import { useWindowSize } from '@vueuse/core'
import { computed, effectScope, reactive, ref, shallowRef, toRefs, watch, watchEffect } from 'vue'
import { numberCardRows, numberReadings } from '../charts/adapter/number'
import useChart, { type Chart } from '../charts/chart'
import {
	FILTER_TYPE_KINDS,
	operatorOf,
	type Filter,
} from '../components/filter_picker/filter_picker'
import useChartPreview from '../charts/chart_preview'
import {
	useSharedChart,
	type ChartReadSurface,
	type DashboardFilterContext,
} from '../charts/chart_read'
import { getUniqueId, safeJSONParse, showErrorToast, store, waitUntil } from '../helpers'
import useDocumentResource from '../helpers/resource'
import router from '../router'
import session from '../session'
import { useTelemetry } from '@framework/ui/telemetry/index.ts'
import type { NumberChartConfig } from '../types/chart.types'
import { FilterOperator, FilterValue } from '../types/query.types'
import {
	BreakpointKey,
	InsightsDashboardv3,
	ViewerFilters,
	Layout,
	WorkbookChart,
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
} from '../types/workbook.types'
import type { CellRules } from './grid_placement'
import {
	BASE_BREAKPOINT,
	derivedPlacement,
	GRID_COLUMNS,
	layoutRank,
	ROW_HEIGHT,
	sameBox,
	writePlacement,
} from './grid_placement'

/**
 * A filter link, `` `query`.`column` ``, split back into its two halves.
 *
 * The only client-side reader of the format, and only the filter editor needs
 * it: it previews values for a link the document has not saved, and the server
 * will not serve those — nothing has made that column a filter yet. Every other
 * surface names the filter and lets the server find the column behind it.
 */
export function parseFilterLink(link: string) {
	const match = link?.match(/^`([^`]+)`\.`([^`]+)`$/)
	return match ? { query: match[1], column: match[2] } : null
}

/**
 * The narrowest window the grid can be arranged in. Below it the layout is the
 * derived one, which is not the author's to save.
 */
const ARRANGEABLE_WIDTH = 1058

/** Columns a Number cell is dropped at: a fifth of the grid, so five read as a row of cards. */
const NUMBER_CARD_COLUMNS = 4

/** Columns a filter cell takes. */
const FILTER_WIDTH = 4

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
const FILTER_ROWS = Math.ceil((FILTER.trigger + FILTER.cellPadding) / ROW_HEIGHT)

const dashboards = new Map<string, Dashboard>()

/**
 * The store one surface reads a dashboard through.
 *
 * `shared` is part of the key, not a flag a page writes: a store outlives the
 * route that made it, and a public link and the in-app page read their cards
 * through different endpoints. Keyed, the surface that asks gets the store that
 * reads its way, whichever mounted first.
 */
export default function useDashboard(name: string, shared = false) {
	const key = `${shared ? 'shared' : 'app'}:${name}`
	const existingDashboard = dashboards.get(key)
	if (existingDashboard) return existingDashboard

	// A store is always first asked for inside a component's `setup`, and it
	// outlives that component. Its own effects (autosave, the chart map, the
	// saved filter states) would stop when the page it was first drawn on
	// unmounts, leaving a store that reads current and saves nothing. Detached,
	// so they live as long as the store does: the map never drops an entry.
	const scope = effectScope(true)
	const dashboard = scope.run(() => makeDashboard(name, shared)) as Dashboard
	dashboards.set(key, dashboard)
	return dashboard
}

function makeDashboard(name: string, isShared: boolean) {
	const { capture } = useTelemetry()
	const dashboard = getDashboardResource(name)

	const editing = ref(false)
	const editingItemIndex = ref<number>()

	// Which breakpoint's layout the author is arranging. Every edit session starts
	// at the widest, because that is the layout every item has and the one the
	// others are derived from.
	const arranging = ref<BreakpointKey>(BASE_BREAKPOINT.key)
	watch(editing, (on) => {
		if (!on) arranging.value = BASE_BREAKPOINT.key
	})

	function isEditingItem(item: WorkbookDashboardItem) {
		return editing.value && editingItemIndex.value === dashboard.doc.items.indexOf(item)
	}

	// When the document saves itself, derived from the state that answers it.
	//
	// A reader never writes, an author mid-edit saves when they are done, and a
	// window too narrow to arrange the grid in would save a layout the author
	// never laid out. Held here because every one of those is this store's own
	// state — a host that set the flag was one more writer of it, and a host that
	// forgot to unset it turned autosave back on for a reader.
	const { width: windowWidth } = useWindowSize()
	watchEffect(() => {
		dashboard.autoSave =
			!dashboard.doc.read_only && !editing.value && windowWidth.value >= ARRANGEABLE_WIDTH
	})

	// Which endpoint the cards read through. The builder and the in-app page draw
	// a card from the config being edited through the authoring endpoint, which
	// needs an authoring seat. A public link has no seat, so its cards read the saved
	// chart through its own `get_data`. The page that mounts the store says.
	const shared = ref(isShared)

	const filterStates = ref<ViewerFilters>({})

	// What a reader filtered one card down to, per chart. It is a filter the
	// reader owns and the document never holds: not saved with the dashboard, and
	// not stored beside the filter states, so a reload clears it.
	const cardFilters = ref<Record<string, Filter[]>>({})

	function cardFiltersOn(chart_name: string): Filter[] {
		return cardFilters.value[chart_name] || []
	}

	function setCardFilters(chart_name: string, filters: Filter[]) {
		cardFilters.value[chart_name] = filters
		refreshChart(chart_name)
	}

	async function addChart(charts: WorkbookChart[]) {
		const maxY = getMaxY()
		for (const chart of charts) {
			const placed = dashboard.doc.items.some(
				(item) => item.type === 'chart' && item.chart === chart.name,
			)
			if (placed) continue
			dashboard.doc.items.push(...(await cellsFor(chart, maxY)))
		}
		capture('dashboard_chart_added')
	}

	/**
	 * The cells a chart is dropped as.
	 *
	 * Every type is one cell except a Number chart: a cell draws one card, so a
	 * chart stating five readings arrives as five cells side by side, each at the
	 * height its own card needs. How many there are is in the config and not in
	 * the list entry, so the chart's document is waited for rather than guessed
	 * at.
	 */
	async function cellsFor(chart: WorkbookChart, y: number): Promise<WorkbookDashboardItem[]> {
		if (chart.chart_type !== 'Number') {
			return [
				{
					type: 'chart',
					chart: chart.name,
					layout: { i: getUniqueId(), x: 0, y, w: 10, h: 20 },
				},
			]
		}

		const doc = useChart(chart.name)
		await waitUntil(() => doc.isloaded)
		const config = doc.doc.config as NumberChartConfig
		// A chart nobody has configured yet is one cell, which is the cell it keeps
		// once its first reading is named.
		const readings: (string | undefined)[] = numberReadings(config)
		if (!readings.length) readings.push(undefined)

		const cells: WorkbookDashboardItem[] = []
		let x = 0
		let rowY = y
		let rowHeight = 0
		for (const reading of readings) {
			if (x + NUMBER_CARD_COLUMNS > GRID_COLUMNS) {
				x = 0
				rowY += rowHeight
				rowHeight = 0
			}
			const h = numberCardRows(config, reading)
			cells.push({
				type: 'chart',
				chart: chart.name,
				...(reading ? { reading } : {}),
				layout: { i: getUniqueId(), x, y: rowY, w: NUMBER_CARD_COLUMNS, h },
			})
			x += NUMBER_CARD_COLUMNS
			rowHeight = Math.max(rowHeight, h)
		}
		return cells
	}

	// A chart store registers itself when it is made (a document resource, an
	// autosave watcher, a debounced history), so it cannot be resolved in a
	// computed, which Vue is free to evaluate, discard or run again. The stores
	// the rules below read are resolved here, once per chart the grid names, the
	// way a cell resolves the one it draws. It is handed out for the same reason:
	// a surface inside the dashboard reads a chart through this map.
	const chartsByName = shallowRef<Record<string, Chart>>({})
	watch(
		() =>
			dashboard.doc.items
				.map((item) => (item.type === 'chart' ? item.chart : ''))
				.filter(Boolean)
				.join(','),
		(names) => {
			const resolved = { ...chartsByName.value }
			let added = false
			for (const chart_name of names ? names.split(',') : []) {
				if (resolved[chart_name]) continue
				resolved[chart_name] = useChart(chart_name)
				added = true
			}
			if (added) chartsByName.value = resolved
		},
		{ immediate: true },
	)

	/**
	 * What the grid is told about a cell beyond its layout.
	 *
	 * A Number cell's height is what the card of the reading it names holds, so the
	 * author sets the width and the height follows the config — including after the
	 * config changes in the workbook. And two of them fit one narrow row, where
	 * every other cell takes the row to itself. A filter cell is its trigger, which
	 * is one height and never anything else.
	 *
	 * Nothing is written back. The height is derived on every read, so a chart
	 * edited in another tab needs no layout save to be drawn at its new height, and
	 * a stored `h` cannot drift from the trigger.
	 */
	const cellRules = computed(() => {
		const rules: CellRules = {}
		for (const item of dashboard.doc.items) {
			if (item.type === 'filter') {
				rules[item.layout.i] = { height: FILTER_ROWS }
				continue
			}
			if (item.type !== 'chart' || !item.chart) continue
			const chart = chartsByName.value[item.chart]
			if (chart?.doc?.chart_type !== 'Number') continue
			rules[item.layout.i] = {
				height: numberCardRows(chart.doc.config as NumberChartConfig, item.reading),
				halfWidth: true,
			}
		}
		return rules
	})

	function getMaxY() {
		return Math.max(...dashboard.doc.items.map((item) => item.layout.y + item.layout.h), 0)
	}

	function addText() {
		const maxY = getMaxY()
		dashboard.doc.items.push({
			type: 'text',
			text: '',
			layout: {
				i: getUniqueId(),
				x: 0,
				y: maxY,
				w: 10,
				h: 5,
			},
		})
		editingItemIndex.value = dashboard.doc.items.length - 1
	}

	function addFilter() {
		const newFilter: WorkbookDashboardItem = {
			type: 'filter',
			filter_name: '',
			filter_type: 'String',
			links: {},
			layout: {
				i: getUniqueId(),
				x: 0,
				y: 0,
				w: FILTER_WIDTH,
				h: FILTER_ROWS,
			},
		}
		dashboard.doc.items.push(newFilter)
		positionNewFilter(newFilter)
		editingItemIndex.value = dashboard.doc.items.length - 1
	}

	function positionNewFilter(newFilter: WorkbookDashboardItem) {
		const items = dashboard.doc.items
		const existingFilters = items.filter((item) => item.type === 'filter' && item !== newFilter)

		if (existingFilters.length === 0) {
			newFilter.layout.x = 0
			newFilter.layout.y = 0
			return
		}

		const topRowY = Math.min(...existingFilters.map((item) => item.layout.y))
		const topRowFilters = existingFilters.filter((item) => item.layout.y === topRowY)
		const rightmostX = Math.max(
			...topRowFilters.map((item) => item.layout.x + (item.layout.w || FILTER_WIDTH)),
			0,
		)

		if (rightmostX + newFilter.layout.w <= GRID_COLUMNS) {
			newFilter.layout.x = rightmostX
			newFilter.layout.y = topRowY
		} else {
			newFilter.layout.x = 0
			newFilter.layout.y = 0

			existingFilters.forEach((item) => {
				item.layout.y += FILTER_ROWS
			})

			const otherItems = items.filter((item) => item.type !== 'filter')
			if (otherItems.length > 0) {
				const minOtherY = Math.min(...otherItems.map((item) => item.layout.y))
				if (minOtherY <= FILTER_ROWS) {
					otherItems.forEach((item) => {
						item.layout.y = Math.max(0, item.layout.y + FILTER_ROWS)
					})
				}
			}
		}
	}

	function removeItem(index: number) {
		dashboard.doc.items.splice(index, 1)
		// The edit cursor is an index into the same list, so a cell removed at or
		// before it leaves it pointing at the cell that moved up.
		if (editingItemIndex.value !== undefined && index <= editingItemIndex.value) {
			editingItemIndex.value = undefined
		}
	}

	// A drag names the breakpoint it arranged. Every breakpoint is dragged on the
	// same grid, so the gesture cannot tell the store where to store it.
	//
	// Only the cells that moved are written, and a cell put back where the
	// breakpoint derives it has its entry dropped. A narrower breakpoint derives
	// every cell it has nothing stored for, and storing a cell that landed where
	// the derived layout puts it would pin it there — one nudge would stop the
	// narrow layout following the wide one, for good.
	//
	// What moved is measured against `before`, the grid the gesture started from,
	// which the grid hands over: a stored layout is not always the layout on
	// screen, and comparing against the stored one calls every cell compaction
	// moved a cell the author moved.
	function moveItems(
		key: BreakpointKey,
		layouts: Layout[],
		before: Layout[],
		verticalCompact = true,
	) {
		const items = dashboard.doc.items
		// Every reference is read before the first one is written: `writePlacement`
		// changes the grid the next reference would be derived against, and a card
		// the author never touched would pick up an entry out of it.
		const references = items.map((_, index) =>
			derivedPlacement(items, key, index, cellRules.value, { verticalCompact }),
		)

		items.forEach((item, index) => {
			const layout = layouts[index]
			if (!layout) return
			const reference = references[index]
			const stood = before[index] && sameBox(before[index], layout)
			// A cell the gesture left where it stood is not written again, with one
			// exception: a stored entry that pins it where the breakpoint already
			// puts it. Compaction can hide that entry's effect, so the drag that
			// releases it is a drag that moves nothing on screen.
			const releases = key !== BASE_BREAKPOINT.key && reference && sameBox(reference, layout)
			if (stood && !releases) return
			writePlacement(item, key, layout, reference)
		})
	}

	function refresh(force = false) {
		// By chart and not by cell: several cells can read one chart, and the read
		// behind them is one.
		linkedCharts().forEach((chart_name) => refreshChart(chart_name, force))
	}

	/** Every chart the grid names, once each. */
	function linkedCharts() {
		const items = dashboard.doc.items.filter((item) => item.type === 'chart')
		return [...new Set(items.map((item) => item.chart))]
	}

	// The card sends what the grid holds, not what it worked out from it: which
	// query a filter lands on is read off the links server-side, the one place it
	// is read for every surface. The items are sent because the builder is editing
	// ones the document has not saved.
	//
	// A card filter goes along as an item and a state of its own. The server has
	// one router for both, so a filter the reader made on a card lands in the
	// chart's query group beside the grid's own, `And`-composed.
	// A card filter is the reader's own, on a column the card draws, so it travels
	// as itself rather than as a filter item the grid never held. The server lands
	// it on the chart's own derived query, which is what the chart's name reaches:
	// the rule falls after the chart's summarize, on the columns the card draws,
	// measures included.
	function filterContextFor(chart_name: string): DashboardFilterContext {
		return {
			chart: chart_name,
			dashboard: dashboard.doc.name,
			items: dashboard.doc.items,
			filters: filterStates.value,
			cardFilters: cardFiltersOn(chart_name).map((filter) => ({
				column: filter.column.name,
				operator: filter.operator,
				value: filter.value,
			})),
		}
	}

	// This grid is a reading surface: the rows its cards draw are narrowed by the
	// filters it holds, so its reads belong to it. Another dashboard drawing the
	// same chart reads its own, and neither moves the other's rows.
	const readSurface: ChartReadSurface = {
		id: `dashboard:${name}`,
		filterContext: filterContextFor,
		canEdit: () => dashboard.doc.has_workbook_access,
	}

	function chartRead(chart_name: string) {
		const chart = useChart(chart_name)
		return shared.value
			? useSharedChart(chart, readSurface)
			: useChartPreview(chart, readSurface)
	}

	function refreshChart(chart_name: string, force = false) {
		const read = chartRead(chart_name)
		read.executionPriority = getLayoutRank(chart_name)
		read.load(force)
	}

	// The chart runs once for every cell that reads it, so it is the cell that
	// reads first that says when — the topmost, leftmost one.
	function getLayoutRank(chart_name: string) {
		const ranks = dashboard.doc.items
			.filter((item) => item.type === 'chart' && item.chart === chart_name)
			.map((item) => layoutRank(item.layout))
		return ranks.length ? Math.min(...ranks) : undefined
	}

	function updateFilterState(
		filter_name: string,
		operator?: FilterOperator,
		value?: FilterValue,
	) {
		const filter = dashboard.doc.items.find(
			(item) => item.type === 'filter' && item.filter_name === filter_name,
		)
		if (!filter) return

		if (!operator) {
			delete filterStates.value[filter_name]
		} else {
			filterStates.value[filter_name] = {
				operator,
				value,
			}
		}

		applyFilter(filter_name)
	}

	/**
	 * Whether a filter says enough to narrow anything, which is the rule the
	 * server states in `_filter_is_set`: an operator, and a value where the
	 * operator asks for one.
	 */
	function isFilterSet(item: WorkbookDashboardFilter): boolean {
		const state = filterStates.value[item.filter_name]
		if (!state?.operator) return false

		const kind = FILTER_TYPE_KINDS[item.filter_type]
		const needsValue = operatorOf(kind, state.operator)?.needsValue ?? true
		return !needsValue || ![undefined, null, ''].includes(state.value as any)
	}

	/** The saved filters that reach one card and are currently set. */
	function filtersOn(chart_name: string): WorkbookDashboardFilter[] {
		return dashboard.doc.items
			.filter((item) => item.type === 'filter')
			.map((item) => item as WorkbookDashboardFilter)
			.filter((item) => Boolean(item.links?.[chart_name]) && isFilterSet(item))
	}

	/**
	 * Whether this card's rows are narrowed by something the reader can undo:
	 * the grid's own filters that reach it, and the filter the reader put on the
	 * card. What the author filtered the chart by is the chart, not a filter.
	 */
	function cardIsFiltered(chart_name: string): boolean {
		return Boolean(filtersOn(chart_name).length || cardFiltersOn(chart_name).length)
	}

	/** Everything `cardIsFiltered` counts, taken off. */
	function resetCardFilters(chart_name: string) {
		const cleared = filtersOn(chart_name)
		cleared.forEach((item) => delete filterStates.value[item.filter_name])
		delete cardFilters.value[chart_name]
		// A grid filter links several cards, so unsetting one from this card is a
		// change to every card it reaches — the same act as answering it, run the
		// same way. The card's own filter reaches nothing else, which is what the
		// last line is for.
		cleared.forEach((item) => applyFilter(item.filter_name))
		refreshChart(chart_name)
	}

	function applyFilter(filter_name: string) {
		const item = dashboard.doc.items.find(
			(item) => item.type === 'filter' && item.filter_name === filter_name,
		)
		if (!item) return

		const filterItem = item as WorkbookDashboardFilter
		const filteredCharts = Object.keys(filterItem.links).filter(
			(chart_name) => filterItem.links[chart_name],
		)
		filteredCharts.forEach((chart_name) => refreshChart(chart_name))
	}

	// The filter names itself and the server finds the column behind it. What the
	// rest of the grid holds goes along unrouted, so the list narrows to what the
	// other filters leave — the server leaves this filter out of its own list.
	function getDistinctColumnValues(
		filter_name: string,
		search_term?: string,
		chart_name?: string,
	) {
		return dashboard.call('get_distinct_column_values', {
			filter_name,
			search_term,
			filter_context: chart_name ? filterContextFor(chart_name) : undefined,
		})
	}

	// A card filter is not a saved filter, so the dashboard cannot find it by name.
	// It is still the dashboard that answers for it: a public reader was published
	// this grid and holds no permission on the query behind a card.
	function getCardColumnValues(chart_name: string, column: string, search_term?: string) {
		return dashboard.call('get_card_column_values', {
			chart: chart_name,
			column,
			search_term,
		})
	}

	function getCardColumnRange(chart_name: string, column: string) {
		return dashboard.call('get_card_column_range', { chart: chart_name, column })
	}

	function getFilterColumnRange(filter_name: string) {
		return dashboard.call('get_filter_column_range', { filter_name })
	}

	function getShareLink() {
		const { href } = router.resolve({
			name: 'SharedDashboard',
			params: { dashboard_name: dashboard.doc.name },
		})
		return dashboard.doc.share_link || `${window.location.origin}${href}`
	}

	function updateAccess(data: {
		is_public: boolean
		is_shared_with_organization: boolean
		people_with_access: string[]
	}) {
		return dashboard
			.call('update_access', { data })
			.catch(showErrorToast)
			.then(() => dashboard.load())
	}

	const key = `insights:dashboard-filter-states-${name}`
	filterStates.value = store(key, () => filterStates.value)

	// The author's default is what a filter opens on, not what it returns to: a
	// reader who has picked something has an entry of their own, and `store` gave
	// it back above. A default seeds a filter the reader has not answered.
	waitUntil(() => dashboard.isloaded).then(() => {
		const defaults = defaultFilterStates(dashboard.doc.items)
		Object.entries(defaults).forEach(([filter_name, state]) => {
			if (filter_name in filterStates.value) return
			filterStates.value[filter_name] = state
		})
	})

	return reactive({
		...toRefs(dashboard),

		editing,
		editingItemIndex,
		cellRules,
		isEditingItem,
		shared,
		arranging,

		filterStates,
		cardFilters,
		cardFiltersOn,
		setCardFilters,
		cardIsFiltered,
		resetCardFilters,
		getCardColumnValues,
		getCardColumnRange,
		getFilterColumnRange,

		addChart,
		addText,
		addFilter,
		removeItem,
		moveItems,

		refresh,
		refreshChart,
		chartRead,
		linkedCharts,
		chartsByName,

		updateFilterState,
		applyFilter,

		getDistinctColumnValues,
		updateAccess,

		getShareLink,
	})
}

export type Dashboard = ReturnType<typeof makeDashboard>

const INITIAL_DOC: InsightsDashboardv3 = {
	doctype: 'Insights Dashboard v3',
	name: '',
	owner: '',
	title: '',
	workbook: '',
	items: [],
	is_public: false,
	is_shared_with_organization: false,
	people_with_access: [],
	read_only: false,
	// the document states what a new dashboard is, so the doctype's default never
	// reaches it: an insert sends every key, and Frappe fills a default only where
	// the value came in unset
	vertical_compact_layout: true,
	has_workbook_access: false,
}

function getDashboardResource(name: string) {
	const doctype = 'Insights Dashboard v3'
	const dashboard = useDocumentResource<InsightsDashboardv3>(doctype, name, {
		initialDoc: { ...INITIAL_DOC, name },
		enableAutoSave: true,
		disableLocalStorage: true,
		transform(doc: any) {
			doc.items = safeJSONParse(doc.items) || []
			return doc
		},
	})
	if (session.isLoggedIn) {
		dashboard.onAfterLoad(() => dashboard.call('track_view').catch(() => {}))
	}
	return dashboard
}

/**
 * What every filter on a dashboard opens on, as its author set it.
 *
 * Whether a default says enough to run is the operator's answer, not the
 * value's — `is_set` asks about the column itself and carries no value, which is
 * the same rule the server states in `_filter_is_set`.
 */
export function defaultFilterStates(items: WorkbookDashboardItem[]): ViewerFilters {
	const states: ViewerFilters = {}
	items.forEach((item) => {
		if (item.type != 'filter') return
		const filterItem = item as WorkbookDashboardFilter

		const operator = filterItem.default_operator
		if (!operator) return
		const kind = FILTER_TYPE_KINDS[filterItem.filter_type]
		const needsValue = operatorOf(kind, operator)?.needsValue ?? true
		if (needsValue && !filterItem.default_value) return

		states[filterItem.filter_name] = {
			operator,
			value: filterItem.default_value,
		}
	})
	return states
}

export function newDashboard() {
	return getDashboardResource('new-dashboard-' + getUniqueId())
}
