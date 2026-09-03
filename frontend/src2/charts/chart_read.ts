// One chart as anything that draws it reads it: the config it draws itself from,
// and the rows the server ran for it.
//
// Two feeds fill it. A public link names the saved chart to its own `get_data`,
// which answers rows and nothing else — a reader never says what query to run,
// and never learns what ran. The builder has no saved chart to name, so it sends
// the config it is editing to `insights.api.authoring` and gets the derived
// operations back with the rows. That door is closed to anyone without an
// authoring seat.
//
// Above the fetch the two are the same store: the same result, the same
// loading, failure and empty states, the same freshness stamp, the same
// priority-queued execution.

import { call } from 'frappe-ui'
import { computed, reactive, ref, unref, type ComputedRef } from 'vue'
import { getErrorMessage } from '../helpers'
import { isServerBusyError, scheduleQueryExecution } from '../query/execution_queue'
import { EMPTY_RESULT, formatResultRows } from '../query/helpers'
import type { AdhocFilters, Operation, QueryResult } from '../types/query.types'
import type { ChartType } from '../types/chart.types'
import type {
	InsightsChartv3,
	ViewerFilters,
	WorkbookDashboardItem,
} from '../types/workbook.types'
import type { Chart } from './chart'
import type { RecordLinks } from './record_link'
import type { DrillDimension, DrillLevel, DrillLevelData, DrillSubject } from './drill/drill_stack'
import { labelWindowRows } from './window'

/**
 * What a card on the builder's dashboard grid needs to have the grid's filters
 * applied to it. It goes to the server unrouted: the links that say which query
 * a filter lands on are read there, for a reader and an author alike. The
 * builder sends the items because it is editing ones it has not saved.
 */
export type DashboardFilterContext = {
	chart: string
	items: WorkbookDashboardItem[]
	filters: ViewerFilters
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
	// a windowed number card's series, from the second execution that splits its
	// window. Absent for every card that draws its sparkline from its own rows
	sparkline?: { columns?: QueryResult['columns']; rows?: QueryResult['rows'] }
	time_taken?: number
	executed_at?: string
	// the authoring feed alone answers these
	operations?: Operation[]
	sql?: string
	use_live_connection?: boolean
	// where the grid's filters landed, as the server routed them
	adhoc_filters?: AdhocFilters
	// what a segment click may break the card down by. It rides along with the
	// rows because a menu that has to ask first puts a round trip in the one place
	// latency is felt — between the click and the menu.
	drill?: { dimensions: DrillDimension[] }
	// which result columns name a desk document, when the rows are documents. A
	// grid draws them as links. Every other chart type ignores them.
	record_links?: RecordLinks
}

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
	// one level of a drill, through the door this feed came in by. The stack the
	// dialog holds is the whole of the request. No operations cross either way,
	// except back out of the authoring door.
	fetchDrillData: (
		levels: DrillLevel[],
		filterContext?: DashboardFilterContext,
	) => Promise<DrillLevelData>
}

export function makeChartRead(feed: ChartFeed, priority?: number) {
	// the preview feed hands over the document it is editing, so read it through
	// whichever of the two it is before anything derives from it
	const doc = computed(() => unref(feed.doc))
	const result = ref<QueryResult>({ ...EMPTY_RESULT })
	// the series a windowed card's sparkline is drawn from, when the server ran
	// one for it
	const sparklineResult = ref<QueryResult>()
	// what the server ran, on the feed that is allowed to say
	const operations = ref<Operation[]>([])
	// where the grid's filters landed, as the server routed them. A level lifted
	// into the query builder needs the same narrowing applied to it.
	const routedFilters = ref<AdhocFilters>()
	// why the chart cannot be drawn yet, as the server read the config
	const configErrors = ref<string[]>([])
	// the columns a segment click may break this card down by
	const drillDimensions = ref<DrillDimension[]>([])
	// the columns of these rows that name a document, when any of them do
	const recordLinks = ref<RecordLinks>()

	const ready = ref(false)
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

	// both set by whoever owns the layout the card sits in
	const executionPriority = ref(priority)
	const filterContext = ref<DashboardFilterContext>()

	let currentLoad = 0
	// the question the rows on screen answer, so the same one is not asked twice
	let lastRequestKey: string | undefined

	async function load(force = false) {
		const requestKey = feed.requestKey?.(filterContext.value)
		if (!force && requestKey !== undefined && requestKey === lastRequestKey) return
		lastRequestKey = requestKey

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
		const dataLoad = scheduleQueryExecution(() => feed.fetchData(force, filterContext.value), {
			isStale,
			priority: executionPriority.value,
		})

		try {
			await docLoad
			if (isStale()) return

			const response = await dataLoad
			if (isStale() || !response) return

			configErrors.value = response.errors || []
			// a half-configured chart is the builder's normal state, and the rows
			// it last drew no longer answer the config on screen. The card says
			// what is missing where the picture was.
			if (configErrors.value.length) return

			const rows = {
				...EMPTY_RESULT,
				columns: response.columns || [],
				rows: response.rows || [],
			}
			result.value = {
				...rows,
				executedSQL: response.sql || '',
				// The window column comes back with no granularity, because the rows
				// are grouped by window and not by a grain. The config is what says
				// how long a window is, so it is what names them.
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
				totalRowCount: rows.rows.length,
				timeTaken: response.time_taken || 0,
				lastExecutedAt: new Date(response.executed_at || Date.now()),
			}
			sparklineResult.value = response.sparkline
				? {
						...EMPTY_RESULT,
						columns: response.sparkline.columns || [],
						rows: response.sparkline.rows || [],
					}
				: undefined
			operations.value = response.operations || []
			routedFilters.value = response.adhoc_filters
			drillDimensions.value = response.drill?.dimensions || []
			recordLinks.value = response.record_links
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
			result.value = { ...EMPTY_RESULT }
			sparklineResult.value = undefined
		} finally {
			if (!isStale()) executing.value = false
		}
	}

	// Everything the drill dialog needs from this card. The card knows the shape a
	// click is read against and the candidates a breakdown may offer. The feed
	// knows the door. Nothing above has to hold both halves.
	const drillSubject = computed<DrillSubject>(() => ({
		chart: { chart_type: doc.value.chart_type as ChartType, config: doc.value.config },
		title: doc.value.title,
		dimensions: drillDimensions.value,
		fetch: (levels) => feed.fetchDrillData(levels, filterContext.value),
	}))

	return reactive({
		doc: feed.doc,
		result,
		sparklineResult,
		// the whole result comes back in one response, so the table it feeds has
		// one page and filters over the rows it holds
		currentOperations: operations,
		routedFilters,
		configErrors,
		drillDimensions,
		recordLinks,
		drillSubject,

		ready,
		executing,
		failed,
		serverBusy,
		failure,
		empty,
		executedAt,
		executionPriority,
		filterContext,

		load,
	})
}

export type ChartRead = ReturnType<typeof makeChartRead>

// one read per chart, so a shared dashboard's cards and the chart's own page
// draw the same card from the same rows
const shared = new Map<string, ChartRead>()

/**
 * The read feed for a public link: the saved chart, fetched through its own
 * `get_data` method by way of `run_doc_method`, which is where a guest's access
 * to a published chart is decided. The document itself comes with the chart
 * store, which a public link already loads the same way.
 *
 * No drill: a public chart stays a picture, and the endpoint that would answer
 * a level needs an authoring seat.
 */
export function useSharedChart(chart: Chart) {
	const key = String(chart.doc.name)
	const existing = shared.get(key)
	if (existing) return existing

	const read = makeChartRead({
		doc: computed(() => chart.doc as ChartReadDoc),
		fetchData: (force, filterContext) =>
			call('insights.api.run_doc_method', {
				method: 'get_data',
				docs: { doctype: 'Insights Chart v3', name: chart.doc.name },
				args: {
					force,
					page_size: chart.doc.config.limit || 100,
					// unrouted: the server reads the links and decides which query
					// each filter lands on, the same way it does for the builder
					chart_name: filterContext?.chart,
					dashboard_items: filterContext?.items,
					filters: filterContext?.filters,
				},
			}).then((response: any) => response.message),
		fetchDrillData: () => Promise.reject(new Error('A public chart cannot be drilled')),
	})
	shared.set(key, read)
	return read
}
