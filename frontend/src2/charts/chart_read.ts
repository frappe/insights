// One chart as anything that draws it reads it: the config it draws itself from,
// and the rows the server ran for it.
//
// Two feeds fill it. A saved chart names itself to `insights.api.viewer`, which
// answers rendering and nothing else — a reader never says what query to run,
// and never learns what ran. The builder has no saved chart to name, so it sends
// the config it is editing to `insights.api.authoring` and gets the derived
// operations back with the rows. That is the one door they come through, and it
// is closed to anyone without an authoring seat.
//
// Above the fetch the two are the same store: the same result, the same
// loading, failure and empty states, the same freshness stamp, the same
// priority-queued execution.

import { call } from 'frappe-ui'
import { computed, reactive, ref, type ComputedRef } from 'vue'
import type { ViewerFilters } from '../dashboard/viewer'
import { isServerBusyError, scheduleQueryExecution } from '../query/execution_queue'
import { EMPTY_RESULT, formatResultRows } from '../query/helpers'
import type { DrillDownSource, Query } from '../query/query'
import type {
	AdhocFilters,
	Operation,
	QueryResult,
	QueryResultColumn,
	QueryResultRow,
} from '../types/query.types'
import type { InsightsChartv3, WorkbookDashboardItem } from '../types/workbook.types'
import { normalizeChartConfig } from './helpers'

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
	time_taken?: number
	executed_at?: string
	// the authoring feed alone answers these
	operations?: Operation[]
	sql?: string
	use_live_connection?: boolean
	// where the grid's filters landed, as the server routed them
	adhoc_filters?: AdhocFilters
}

export type ChartFeed = {
	doc: ChartReadDoc | ComputedRef<ChartReadDoc>
	// the saved feed draws its frame from a second round trip; the preview feed
	// already holds the document it is editing
	fetchDoc?: () => Promise<void>
	fetchData: (
		force: boolean,
		filterContext?: DashboardFilterContext,
	) => Promise<ChartDataResponse | undefined>
	// forking what the server ran into a drill query is authoring, and so is the
	// query editor it opens in. The feed that receives the operations is the feed
	// that carries it — a read surface has neither, which is ticket 11's business.
	// `row` is the raw row, as a chart's own click events report it.
	drillDown?: (
		source: DrillDownSource,
		column: QueryResultColumn,
		row: QueryResultRow,
	) => Promise<Query | undefined>
}

export function makeChartRead(feed: ChartFeed, priority?: number) {
	const result = ref<QueryResult>({ ...EMPTY_RESULT })
	// what the server ran, on the feed that is allowed to say. Drill-down forks it.
	const operations = ref<Operation[]>([])
	const useLiveConnection = ref(false)
	// where the grid's filters landed, as the server routed them. A drill-down
	// forks the operations above and needs the same narrowing applied to them.
	const routedFilters = ref<AdhocFilters>()
	// why the chart cannot be drawn yet, as the server read the config
	const configErrors = ref<string[]>([])

	const ready = ref(false)
	const executing = ref(true)
	const failed = ref(false)
	const serverBusy = ref(false)
	// when the rows on screen were produced. It is the card that knows, so the
	// page's freshness stamp is read off the cards
	const executedAt = ref<Date>()
	const empty = computed(() => ready.value && !result.value.rows.length)

	// both set by whoever owns the layout the card sits in
	const executionPriority = ref(priority)
	const filterContext = ref<DashboardFilterContext>()

	let currentLoad = 0

	async function load(force = false) {
		executing.value = true
		failed.value = false
		serverBusy.value = false

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
			// a half-configured chart is the builder's normal state: say what is
			// missing and leave the last picture up, rather than blanking the card
			if (configErrors.value.length) return

			const rows = {
				...EMPTY_RESULT,
				columns: response.columns || [],
				rows: response.rows || [],
			}
			result.value = {
				...rows,
				executedSQL: response.sql || '',
				formattedRows: formatResultRows(rows, response.granularity || {}),
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
			operations.value = response.operations || []
			useLiveConnection.value = Boolean(response.use_live_connection)
			routedFilters.value = response.adhoc_filters
			executedAt.value = result.value.lastExecutedAt
			ready.value = true
		} catch (error) {
			// a load a newer one has superseded is not a failure — and while it
			// waited in the queue it dropped out rather than spending a slot on a
			// result nobody is waiting for
			if (isStale()) return
			serverBusy.value = isServerBusyError(error)
			failed.value = true
			result.value = { ...EMPTY_RESULT }
		} finally {
			if (!isStale()) executing.value = false
		}
	}

	async function getDrillDownQuery(
		column: QueryResultColumn,
		row: QueryResultRow,
	): Promise<Query | undefined> {
		if (!feed.drillDown || !operations.value.length) return
		return feed.drillDown(
			{
				operations: operations.value,
				result: result.value,
				use_live_connection: useLiveConnection.value,
			},
			column,
			row,
		)
	}

	return reactive({
		doc: feed.doc,
		result,
		// the whole result comes back in one response, so the table it feeds has
		// one page and filters over the rows it holds
		currentOperations: operations,
		routedFilters,
		configErrors,

		ready,
		executing,
		failed,
		serverBusy,
		empty,
		executedAt,
		executionPriority,
		filterContext,

		load,
		getDrillDownQuery,
	})
}

export type ChartRead = ReturnType<typeof makeChartRead>

export type SavedChartOptions = {
	// the dashboard the chart is being viewed on, if any. It carries the chart's
	// audience and is what makes filter state routable.
	dashboard?: string
	filters?: () => ViewerFilters | undefined
	// where this card sits on the grid, so the queue serves the top of the page
	// before the bottom
	priority?: number
}

export function useSavedChart(reference: string, options: SavedChartOptions = {}) {
	const doc = reactive<ChartReadDoc>({
		name: reference,
		title: '',
		chart_type: '',
		config: normalizeChartConfig({}, ''),
		can_edit: false,
	})

	return makeChartRead(
		{
			doc,
			fetchDoc: async () => {
				const chart_doc = await call('insights.api.viewer.get_chart', {
					chart: reference,
					dashboard: options.dashboard,
				})
				Object.assign(doc, chart_doc)
				doc.config = normalizeChartConfig(chart_doc.config || {}, chart_doc.chart_type)
			},
			fetchData: (force) =>
				call('insights.api.viewer.get_chart_data', {
					chart: reference,
					dashboard: options.dashboard,
					filters: options.filters?.(),
					force,
				}),
		},
		options.priority,
	)
}
