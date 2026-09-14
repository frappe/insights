// One chart as anything that draws it reads it: the config it draws itself from,
// and the rows the server ran for it.
//
// Two feeds fill it. A public link names the saved chart to its own `get_data`,
// which answers rows and nothing else — a reader never says what query to run,
// and never learns what ran. The builder has no saved chart to name, so it sends
// the config it is editing to `insights.api.authoring` and gets the derived
// operations back with the rows. That endpoint needs an authoring seat.
//
// Above the fetch the two are the same store: the same result, the same
// loading, failure and empty states, the same freshness stamp, the same
// priority-queued execution.

import { call } from 'frappe-ui'
import { computed, reactive, ref, unref, type ComputedRef, type InjectionKey } from 'vue'
import { getErrorMessage } from '../helpers'
import { stableStringify } from '../helpers/stable_stringify'
import { __ } from '../translation'
import session, { type Session } from '../session'
import { isServerBusyError, scheduleQueryExecution } from '../query/execution_queue'
import { emptyResult, formatResultRows } from '../query/helpers'
import type {
	AdhocFilters,
	FilterOperator,
	FilterValue,
	Operation,
	QueryResult,
	QueryResultColumn,
} from '../types/query.types'
import type { ChartType } from '../types/chart.types'
import type { InsightsChartv3, ViewerFilters, WorkbookDashboardItem } from '../types/workbook.types'
import type { Chart } from './chart'
import type { RecordLinks } from './record_link'
import type { DrillDimension, DrillLevel, DrillLevelData, DrillSubject } from './drill/drill_stack'
import { labelWindowRows } from './window'

/**
 * What a card on the builder's dashboard grid needs to have the grid's filters
 * applied to it. It goes to the server unrouted: the links that say which query
 * a filter lands on are read there, for a reader and an author alike. The
 * builder sends the items because it is editing ones it has not saved.
 *
 * A grid is where the saved filters come from, and nothing else: a chart on its
 * own page names itself and the filter the reader put on it, and leaves the
 * rest out.
 */
export type DashboardFilterContext = {
	chart: string
	/** The dashboard drawing this card: the grid whose links route its filters. */
	dashboard?: string
	items?: WorkbookDashboardItem[]
	filters?: ViewerFilters
	/** What the reader narrowed this one card to, on the columns the card draws. */
	cardFilters: CardFilter[]
}

/** A card filter on the wire: a column the card draws, and what to hold it to. */
export type CardFilter = {
	column: string
	operator: FilterOperator
	value: FilterValue
}

// everything a card draws the picture from. The builder's own document is one of
// these, which is what lets the preview feed read straight off what is being edited
export type ChartReadDoc = {
	name: string
	title: string
	chart_type: string
	config: InsightsChartv3['config']
	can_edit?: boolean
}

type ChartDataResponse = {
	errors?: string[]
	columns?: QueryResult['columns']
	rows?: QueryResult['rows']
	granularity?: Record<string, string>
	// a span card's series, from the second execution that splits its
	// period. Absent for every card that draws its sparkline from its own rows
	sparkline?: { columns?: QueryResult['columns']; rows?: QueryResult['rows'] }
	time_taken?: number
	executed_at?: string
	operations?: Operation[]
	sql?: string
	use_live_connection?: boolean
	// where the grid's filters landed, as the server routed them
	adhoc_filters?: AdhocFilters
	// what a segment click may break the card down by. It comes with the rows
	// because a menu that has to ask first puts a round trip in the one place
	// latency is felt — between the click and the menu.
	drill?: { dimensions: DrillDimension[] }
	// which row answers each of a number card's comparisons, keyed by the source
	// that asks it. A row named `null` was asked for and came back empty. A
	// source left out is one the card's period cannot be asked at all
	comparison_rows?: Record<string, number | null>
	// which result columns name a desk document, when the rows are documents. A
	// grid draws them as links. Every other chart type ignores them.
	record_links?: RecordLinks
	// the symbol of every currency code the rows carry, so any code prints
	currency_symbols?: Session['site']['currency_symbols']
}

/**
 * Which surface is reading, when something other than the chart itself is. The
 * rows a surface draws depend on the filters that surface applies, so the
 * surface is half of a read's identity: two dashboards drawing one chart hold
 * one read each, and neither can move the other's rows. A reader that applies
 * nothing names no surface and shares the one unnamed read.
 */
export type ChartReadSurface = {
	id: string
	// the filters this surface applies to the chart it names. It is asked at the
	// moment of the read rather than stored on it, so a load always carries what
	// the surface holds now.
	filterContext: (chart_name: string) => DashboardFilterContext
	// whether this surface authors the chart it draws. Asked at the moment of the
	// read, like the filters: a dashboard learns what its reader may do when its
	// document lands. A surface that leaves it out authors.
	// eslint-disable-next-line no-unused-vars
	canEdit?: () => boolean
}

/** A read is one chart, as one feed's surface reads it. */
function chartReadKey(feed: ChartFeedName, chart: Chart, surface?: ChartReadSurface) {
	return `${feed}:${surface?.id || ''}:${chart.doc.name}`
}

/** Which feed the rows came from: the saved chart's, or the builder's. */
export type ChartFeedName = 'saved' | 'preview'

export type ChartFeed = {
	doc: ChartReadDoc | ComputedRef<ChartReadDoc>
	// the saved feed draws its frame from a second round trip. The preview feed
	// already holds the document it is editing.
	fetchDoc?: () => Promise<void>
	fetchData: (
		force: boolean,
		filterContext?: DashboardFilterContext,
	) => Promise<ChartDataResponse | undefined>
	// What this feed would ask for, as a string. A load that would ask the same
	// question again is dropped before it starts: the rows on screen are already
	// its answer, and running it puts the card through its loading state for a
	// picture that does not change. A feed that leaves it out runs every load.
	requestKey?: (filterContext?: DashboardFilterContext) => string
	// one level of a drill, through this feed's endpoint. The stack the dialog
	// holds is the whole request. No operations cross either way, except back out
	// of the authoring endpoint.
	fetchDrillData: (
		levels: DrillLevel[],
		filterContext?: DashboardFilterContext,
	) => Promise<DrillLevelData>
	// whether this feed answers a drill at all. A card draws the affordance only
	// where it leads somewhere, the way a table's sort is drawn only where the
	// surface holds the config.
	drillable?: boolean
}

export function makeChartRead(
	feed: ChartFeed,
	// the surface this read belongs to: what it narrows the chart by, asked on
	// every load
	surface?: ChartReadSurface,
) {
	// the preview feed hands over a ref to the document it is editing
	const doc = computed(() => unref(feed.doc))

	function filterContext(): DashboardFilterContext | undefined {
		return surface?.filterContext(doc.value.name)
	}
	const result = ref<QueryResult>(emptyResult())
	// the series a span card's sparkline is drawn from, when the server ran
	// one for it
	const sparklineResult = ref<QueryResult>()
	const operations = ref<Operation[]>([])
	// where the grid's filters landed, as the server routed them. A level lifted
	// into the query builder needs the same narrowing applied to it.
	const routedFilters = ref<AdhocFilters>()
	// why the chart cannot be drawn yet, as the server read the config
	const configErrors = ref<string[]>([])
	const drillDimensions = ref<DrillDimension[]>([])
	const recordLinks = ref<RecordLinks>()
	// which row a number card's comparison is measured against, as the server
	// named it. Only the server can say: a span is resolved while the query runs
	const comparisonRows = ref<Record<string, number | null>>()

	const ready = ref(false)
	// the chart behind this read changed, so the rows on screen answer a question
	// nobody is asking any more. It is a mark and not a run: a read whose surface
	// is unmounted has nobody waiting for rows, and the next load runs it whether
	// or not the request it would send has changed.
	const stale = ref(false)
	const executing = ref(true)
	const failed = ref(false)
	const serverBusy = ref(false)
	// what the server said went wrong, for a surface that may show it. A busy
	// server is its own state, so it leaves this empty.
	const failure = ref('')
	// when the rows on screen were produced. It is the card that knows, so the
	// page's freshness stamp is read off the cards
	const executedAt = ref<Date>()
	const empty = computed(() => ready.value && !result.value.rows.length)

	const executionPriority = ref<number>()

	let currentLoad = 0
	// the question the rows on screen answer, so the same one is not asked twice
	let lastRequestKey: string | undefined

	// The rows and what is read off them are one picture, so a load that draws
	// none leaves none: a comparison pairing kept past its rows names a row that
	// is no longer there.
	function clearPicture() {
		result.value = emptyResult()
		sparklineResult.value = undefined
		comparisonRows.value = undefined
	}

	async function load(force = false) {
		const requestKey = feed.requestKey?.(filterContext())
		if (!force && !stale.value && requestKey !== undefined && requestKey === lastRequestKey)
			return
		lastRequestKey = requestKey
		stale.value = false

		executing.value = true
		failed.value = false
		serverBusy.value = false
		failure.value = ''

		const token = ++currentLoad
		const isStale = () => token !== currentLoad

		const docLoad = feed.fetchDoc?.()
		// Every card on a dashboard fires at once, and the server's query limiter
		// turns the surplus away with a 503 rather than queueing them. Nothing is
		// wrong when that happens — the card waits its turn and asks again, on the
		// same queue the query builder uses. A real failure is not retried and
		// reaches the card immediately.
		const dataLoad = scheduleQueryExecution(() => feed.fetchData(force, filterContext()), {
			isStale,
			priority: executionPriority.value,
		})

		try {
			await docLoad
			if (isStale()) return

			const response = await dataLoad
			if (isStale()) return
			// a feed that answers nothing answers nothing about the chart either:
			// the card has no picture and no reason it has none, so it fails and
			// the reader can ask again
			if (!response) throw new Error(__('This chart could not be loaded'))

			configErrors.value = response.errors || []
			// a half-configured chart is the builder's normal state, and the rows
			// it last drew no longer answer the config on screen. The card says
			// what is missing where the picture was.
			if (configErrors.value.length) {
				clearPicture()
				return
			}

			// a carried currency column rides in the row and is read by name; only
			// the listing drops it
			Object.assign(session.site.currency_symbols, response.currency_symbols || {})
			const rows = {
				...emptyResult(),
				columns: withoutHidden(response.columns),
				rows: response.rows || [],
			}
			result.value = {
				...rows,
				executedSQL: response.sql || '',
				// The period column comes back with no granularity, because the rows
				// are grouped by span and not by a grain. The config is what says
				// how long a span is, so it is what names them.
				formattedRows: labelWindowRows(
					formatResultRows(rows, response.granularity || {}),
					doc.value.chart_type,
					doc.value.config,
				),
				columnOptions: rows.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
					query: '',
					data_type: column.type,
				})),
				// the page's length is not the count, and a reader that takes it for
				// one stops at the first page. Nothing here says how many rows there
				// are, so nothing claims to.
				totalRowCount: 0,
				timeTaken: response.time_taken || 0,
				lastExecutedAt: new Date(response.executed_at || Date.now()),
			}
			sparklineResult.value = response.sparkline
				? {
						...emptyResult(),
						columns: withoutHidden(response.sparkline.columns),
						rows: response.sparkline.rows || [],
				  }
				: undefined
			operations.value = response.operations || []
			routedFilters.value = response.adhoc_filters
			drillDimensions.value = response.drill?.dimensions || []
			recordLinks.value = response.record_links
			comparisonRows.value = response.comparison_rows
			executedAt.value = result.value.lastExecutedAt
			ready.value = true
		} catch (error) {
			// a load a newer one has superseded is not a failure — and while it
			// waited in the queue it dropped out rather than spending a slot on a
			// result nobody is waiting for
			if (isStale()) return
			// nothing on screen answers this question, so asking it again is not a
			// repeat
			lastRequestKey = undefined
			serverBusy.value = isServerBusyError(error)
			failure.value = serverBusy.value ? '' : getErrorMessage(error)
			failed.value = true
			clearPicture()
		} finally {
			if (!isStale()) executing.value = false
		}
	}

	// Everything the drill dialog needs from this card. The card knows the shape a
	// click is read against and the candidates a breakdown may offer. The feed
	// knows the endpoint. Nothing above holds both halves.
	const drillSubject = computed<DrillSubject>(() => ({
		chart: { chart_type: doc.value.chart_type as ChartType, config: doc.value.config },
		title: doc.value.title,
		dimensions: drillDimensions.value,
		fetch: (levels) => feed.fetchDrillData(levels, filterContext()),
	}))

	const drillable = feed.drillable ?? true

	return reactive({
		doc: feed.doc,
		drillable,
		result,
		sparklineResult,
		currentOperations: operations,
		routedFilters,
		configErrors,
		drillDimensions,
		recordLinks,
		comparisonRows,
		drillSubject,

		ready,
		stale,
		executing,
		failed,
		serverBusy,
		failure,
		empty,
		executedAt,
		executionPriority,

		load,
	})
}

export type ChartRead = ReturnType<typeof makeChartRead>

/**
 * The read the chart builder draws, as the forms under it reach it.
 *
 * A key and not a string: the type travels with it, so a form that injects it
 * cannot name a read that was never provided.
 */
export const chartPreviewKey: InjectionKey<ChartRead> = Symbol('chartPreview')

// One read per chart per surface per feed: the cards of one shared dashboard
// draw from the same rows, a second dashboard reading the same chart holds its
// own, and the builder's preview of that chart is a read beside both. Both
// feeds cache here, because what goes stale is the chart and not one of its
// reads.
const reads = new Map<string, { chart: string; read: ChartRead }>()

/**
 * The read behind one feed's surface, made on the first caller that asks for it.
 *
 * The key is built here rather than passed in: it is what tells one read from
 * another, and a caller free to hand over a key that disagrees with the chart
 * beside it can file a read where nothing invalidating that chart will find it.
 */
export function cachedChartRead(
	feed: ChartFeedName,
	chart: Chart,
	surface: ChartReadSurface | undefined,
	make: () => ChartRead,
): ChartRead {
	const key = chartReadKey(feed, chart, surface)
	const existing = reads.get(key)
	if (existing) return existing.read

	const read = make()
	reads.set(key, { chart: String(chart.doc.name), read })
	return read
}

/**
 * Re-file a chart's reads under the name its insert gave it.
 *
 * A read made while the chart was unsaved is keyed on `new-chart-<id>`, and
 * every invalidation after the insert names the real chart. Without this the
 * mark reaches nothing, and the card that drew the rows runs the query again.
 */
export function renameChartReads(from: string, to: string) {
	if (!from || !to || from === to) return
	for (const [key, entry] of [...reads]) {
		if (entry.chart !== from) continue
		reads.delete(key)
		reads.set(`${key.slice(0, key.length - from.length)}${to}`, { chart: to, read: entry.read })
	}
}

/**
 * Mark every read of one chart stale.
 *
 * Chart identity is what goes stale: a chart edited in the builder is the same
 * chart the dashboard beside it draws, and that read asks the same question it
 * asked before, so a plain load would be dropped as a repeat. The mark is what
 * lets it through.
 *
 * Marked and not run, because the reads live longer than the surfaces that made
 * them: running every one puts a query per dashboard nobody is looking at on
 * the server, for rows that will have gone stale again by the time a card draws
 * them. A surface that mounts loads what it draws, and finds the mark waiting.
 */
function withoutHidden(columns?: QueryResultColumn[]): QueryResultColumn[] {
	return (columns || []).filter((column) => !column.hidden)
}

export function invalidateChart(chart_name: string) {
	reads.forEach((entry) => {
		if (entry.chart === chart_name) entry.read.stale = true
	})
}

/**
 * The read feed for a public link: the saved chart, fetched through its own
 * `get_data` method by way of `run_doc_method`, which is where a guest's access
 * to a published chart is decided. The document itself comes with the chart
 * store, which a public link already loads the same way.
 *
 * No drill: a public chart stays a picture, and the endpoint that would answer
 * a level needs an authoring seat.
 */
export function useSharedChart(chart: Chart, surface?: ChartReadSurface) {
	return cachedChartRead('saved', chart, surface, () => makeSharedChart(chart, surface))
}

function makeSharedChart(chart: Chart, surface?: ChartReadSurface) {
	// A reader changes none of the config, so what the server is asked for is the
	// chart's name and the narrowing the surface put on it.
	const request = (filterContext?: DashboardFilterContext) => ({
		chart_name: chart.doc.name,
		page_size: chart.doc.config.limit || 100,
		// unrouted: the server reads the links under this chart's own name and
		// decides which query each filter lands on. The routing table is not sent —
		// a share link names the dashboard it opens and the server reads that
		// dashboard's stored links.
		dashboard: filterContext?.dashboard,
		filters: filterContext?.filters,
		card_filters: filterContext?.cardFilters,
	})

	return makeChartRead(
		{
			// a public link draws a picture and nothing else
			doc: computed(() => ({ ...chart.doc, can_edit: false }) as ChartReadDoc),
			// A number card is one cell per reading, and every cell loads the chart
			// it draws. Without a key each of them is a separate execution of the one
			// query.
			requestKey: (filterContext) => stableStringify(request(filterContext)),
			fetchData: (force, filterContext) => {
				const { chart_name, ...args } = request(filterContext)
				return call('insights.api.run_doc_method', {
					method: 'get_data',
					docs: { doctype: 'Insights Chart v3', name: chart_name },
					args: { force, ...args },
				}).then((response: any) => response.message)
			},
			drillable: false,
			fetchDrillData: () => Promise.reject(new Error('A public chart cannot be drilled')),
		},
		surface,
	)
}
