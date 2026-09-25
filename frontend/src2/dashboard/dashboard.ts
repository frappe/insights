import { useWindowSize } from '@vueuse/core'
import { call } from 'frappe-ui'
import { computed, effectScope, reactive, ref, shallowRef, toRefs, watch, watchEffect } from 'vue'
import { numberCardRows, numberReadings } from '../charts/adapter/number'
import useChart, { type Chart } from '../charts/chart'
import {
	FILTER_TYPE_KINDS,
	operatorOf,
	type Filter,
} from '../components/filter_picker/filter_picker'
import useChartPreview, { type ChartPreviewSurface } from '../charts/chart_preview'
import { type DashboardFilterContext } from '../charts/chart_view'
import { getUniqueId, safeJSONParse, showErrorToast, waitUntil } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import { __ } from '../translation'
import useDocumentResource from '../helpers/resource'
import router from '../router'
import { useTelemetry } from '../telemetry'
import type { NumberChartConfig } from '../types/chart.types'
import { FilterOperator, FilterValue } from '../types/query.types'
import {
	BreakpointKey,
	FilterValues,
	InsightsDashboardv3,
	Layout,
	WorkbookChart,
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
} from '../types/workbook.types'
import {
	BASE_BREAKPOINT,
	derivedPlacement,
	GRID_COLUMNS,
	layoutRank,
	sameBox,
	writePlacement,
} from './grid_placement'
import { cellRulesFor, defaultFilterStates, FILTER_ROWS, invalidateDashboard } from './view'

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

const dashboards = new Map<string, Dashboard>()

/** The store the builder edits a dashboard through, one per dashboard. */
export default function useDashboard(name: string) {
	const key = name
	const existingDashboard = dashboards.get(key)
	if (existingDashboard) return existingDashboard

	// A store is always first asked for inside a component's `setup`, and it
	// outlives that component. Its own effects (autosave, the chart map, the
	// saved filter states) would stop when the page it was first drawn on
	// unmounts, leaving a store that reads current and saves nothing. Detached,
	// so they live as long as the store does: the map never drops an entry.
	const scope = effectScope(true)
	const dashboard = scope.run(() => makeDashboard(name)) as Dashboard
	dashboards.set(key, dashboard)
	return dashboard
}

function makeDashboard(name: string) {
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

	const filterStates = ref<FilterValues>({})

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

	async function addChart(charts: WorkbookChart[], via: 'selector' | 'drag') {
		const maxY = getMaxY()
		let added = 0
		for (const chart of charts) {
			const placed = dashboard.doc.items.some(
				(item) => item.type === 'chart' && item.chart === chart.name,
			)
			if (placed) continue
			dashboard.doc.items.push(...(await cellsFor(chart, maxY)))
			added++
		}
		if (added) {
			capture('dashboard_chart_added', { via, count: added })
		}
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
	 * Grid rules for each cell beyond its layout, from `cellRulesFor`. The builder
	 * derives them from the chart stores it already holds.
	 */
	const cellRules = computed(() =>
		cellRulesFor(dashboard.doc.items, (chart) => chartsByName.value[chart]?.doc),
	)

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

	// The builder's grid renders its cards from the config being edited, not the
	// saved chart, so an unsaved edit shows on the grid too. The reads belong to
	// this dashboard, because its filters narrow their rows. Another dashboard
	// with the same chart has its own reads.
	const viewSurface: ChartPreviewSurface = {
		id: `dashboard:${name}`,
		filterContext: filterContextFor,
		canWrite: () => dashboard.doc.has_workbook_access,
	}

	function chartView(chart_name: string) {
		return useChartPreview(useChart(chart_name), viewSurface)
	}

	function refreshChart(chart_name: string, force = false) {
		const read = chartView(chart_name)
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

	// the view endpoints: card values and ranges come from the saved grid, so the
	// builder needs none of its own
	function getCardColumnValues(chart_name: string, column: string, search_term?: string) {
		return call('insights.api.view.get_card_values', {
			dashboard: dashboard.doc.name,
			chart: chart_name,
			column,
			search_term,
		})
	}

	function getCardColumnRange(chart_name: string, column: string) {
		return call('insights.api.view.get_card_range', {
			dashboard: dashboard.doc.name,
			chart: chart_name,
			column,
		})
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

	// Updates who the document is shared with by name. Other readers come from
	// the `visibility` field, which saves with the rest of the document.
	function updateAccess(data: { people_with_access: string[] }) {
		return dashboard
			.call('update_access', { data })
			.catch(showErrorToast)
			.then(() => dashboard.load())
	}

	// Done. Edit mode ends only after the save returns. Autosave starts as soon
	// as edit mode ends, and a save refused under autosave reverts what was sent.
	// So a refused save keeps edit mode open with every edit.
	async function finishEditing() {
		await dashboard.save()
		editing.value = false
	}

	// Reset Layout. Edit mode ends only after the confirm and the reload of the
	// stored document. Ending it first would start autosave, which would save the
	// edits the author is about to discard. Cancel keeps edit mode open.
	function discardEditing() {
		confirmDialog({
			title: __('Discard Changes'),
			message: __('Are you sure you want to discard changes?'),
			onSuccess: async () => {
				await dashboard.load()
				editing.value = false
			},
		})
	}

	// The owner sees the defaults they set, not their last choice. A default
	// belongs to the document, and the owner is here to check it. A default fills
	// only a filter that has no state yet.
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
		isEditingItem,
		finishEditing,
		discardEditing,
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
		chartView,
		linkedCharts,
		chartsByName,
		cellRules,

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
	visibility: 'Private',
	visible_to_roles: [],
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
	dashboard.onAfterLoad(() =>
		dashboard.call('track_view', { surface: 'workbook' }).catch(() => {}),
	)
	dashboard.onAfterSave(() => invalidateDashboard(String(dashboard.doc.name)))
	return dashboard
}

export function newDashboard() {
	return getDashboardResource('new-dashboard-' + getUniqueId())
}
