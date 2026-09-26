// A saved chart sends its name to `insights.api.view`. The reader never sends
// the query and never gets the operations back. The builder has no saved chart,
// so it sends the config it is editing to `insights.api.authoring` and gets the
// operations back with the rows. Only users with an Insights role may call it.
//
// A read holds the chart and its rows as one snapshot. Only a load that returns
// both replaces it, so a card never renders a config over rows that the config
// did not produce.

import { call } from 'frappe-ui'
import { computed, reactive, ref, shallowRef, unref, type ComputedRef } from 'vue'
import { copy, getErrorMessage } from '../helpers'
import { useResultExport } from '../helpers/result_export'
import { stableStringify } from '../helpers/stable_stringify'
import type { NotPermitted } from '../not_permitted'
import { __ } from '../translation'
import session, { type Session } from '../session'
import { isServerBusyError, scheduleQueryExecution } from '../query/execution_queue'
import { emptyResult, formatResultRows } from '../query/helpers'
import type {
	FilterOperator,
	FilterValue,
	Operation,
	QueryResult,
	QueryResultColumn,
} from '../types/query.types'
import type { ChartType } from '../types/chart.types'
import type { InsightsChartv3, FilterValues, WorkbookDashboardItem } from '../types/workbook.types'
import type { RecordLinks } from './record_link'
import type {
	DrillDimension,
	DrillLevel,
	DrillLevelData,
	DrillRowsSource,
	DrillSubject,
} from './drill/drill_stack'
import {
	downloadViewDrillRows,
	fetchViewDrillData,
	fetchViewDrillRowsRange,
	fetchViewDrillRowsValues,
} from './drill/drill_api'
import { normalizeChartConfig } from './helpers'
import { labelWindowRows } from './window'

/**
 * The server reads the dashboard's filter links to decide which query each
 * filter applies to, for readers and authors alike. The builder sends `items`
 * because it may hold unsaved edits.
 *
 * A chart on its own page has no dashboard. It sends only its name and its card
 * filters.
 */
export type DashboardFilterContext = {
	chart: string
	dashboard?: string
	items?: WorkbookDashboardItem[]
	filters?: FilterValues
	cardFilters: CardFilter[]
}

export type CardFilter = {
	column: string
	operator: FilterOperator
	value: FilterValue
}

// The builder's chart document has this shape too, so the preview source reads
// it directly.
export type ChartViewDoc = {
	name: string
	title: string
	chart_type: string
	config: InsightsChartv3['config']
	can_write?: boolean
	// a drill sends it back
	modified?: string
	// set only on the builder's document. A View never gets the query
	query?: string
}

type ChartDataResponse = {
	chart?: ChartViewDoc
	errors?: string[]
	columns?: QueryResult['columns']
	rows?: QueryResult['rows']
	granularity?: Record<string, string>
	// a span card's series, from a second execution that splits its period.
	// Absent when the card renders its sparkline from its own rows
	sparkline?: { columns?: QueryResult['columns']; rows?: QueryResult['rows'] }
	time_taken?: number
	executed_at?: string
	operations?: Operation[]
	sql?: string
	use_live_connection?: boolean
	// what a segment click may break the card down by. It comes with the rows so
	// that the menu opens without a round trip after the click.
	// `can_rows` says whether this reader may see the rows behind a segment. The
	// server decides it, so the menu shows the rows action only when it is true.
	drill?: { dimensions: DrillDimension[]; can_rows?: boolean }
	// the server refuses a card filter on a chart that runs as its owner, so the
	// card shows the filter only when this is true
	can_filter?: boolean
	// whether this reader may see more than the chart: pages after the first, and
	// the row count. Absent means yes, as for `drill.can_rows`
	can_read_rows?: boolean
	can_export?: boolean
	// the row each comparison of a Number card measures against, keyed by
	// comparison. `null` means the server asked and got no row. A missing key
	// means the card's period does not allow that comparison
	comparison_rows?: Record<string, number | null>
	record_links?: RecordLinks
	// an answer, not a failure: there is nothing to retry
	not_permitted?: NotPermitted
	user_permissions?: { doctype: string; documents: string[] }[]
	// a team's Table Restriction, or a column blanked on the rows only desk
	// allows, filtered these rows. Unlike `user_permissions`, it names nothing
	narrowed_by_permissions?: boolean
	currency_symbols?: Session['site']['currency_symbols']
	// the date this card's spans resolved against. A span is stored unresolved,
	// so the card needs this to say which dates its number covers
	read_on?: string
	// builder only: the `modified` of the saved chart these rows ran as
	modified?: string
}

/**
 * The dashboard or page that reads a chart with its own filters. The filters
 * decide the rows, so they are part of a read's key: two dashboards that show
 * one chart hold one read each and cannot change each other's rows. A caller
 * that applies no filters passes none and shares one read.
 */
export type ChartReadContext = {
	id: string
	// called on each load and not stored, so a load always sends the current
	// filters
	filterContext: (chart_name: string) => DashboardFilterContext
}

function chartReadKey(source: ChartSourceName, chart_name: string, context?: ChartReadContext) {
	return `${source}:${context?.id || ''}:${chart_name}`
}

/** `preview` is the builder's source. */
export type ChartSourceName = 'saved' | 'preview'

export type ChartSource = {
	doc: ChartViewDoc | ComputedRef<ChartViewDoc>
	fetchDoc?: () => Promise<ChartViewDoc | undefined>
	takeChartDoc?: (chartDoc: ChartViewDoc) => void
	fetchData: (
		force: boolean,
		filterContext: DashboardFilterContext | undefined,
		page: number,
	) => Promise<ChartDataResponse | undefined>
	fetchCount?: (
		filterContext: DashboardFilterContext | undefined,
		force: boolean,
	) => Promise<number>
	fetchExport?: (format: string, filterContext?: DashboardFilterContext) => Promise<string>
	// The request this source would send, as a string. A load with the same key
	// as the rows on screen is skipped, so the card does not show its loading
	// state for the same result. A source without it runs every load.
	requestKey?: (filterContext?: DashboardFilterContext) => string
	// `rendered` is the chart on screen. Operations are never sent, and only the
	// authoring endpoint returns them.
	fetchDrillData: (
		levels: DrillLevel[],
		filterContext: DashboardFilterContext | undefined,
		rendered: ChartViewDoc,
	) => Promise<DrillLevelData>
	rowsSource?: (
		levels: DrillLevel[],
		filterContext: DashboardFilterContext | undefined,
		rendered: ChartViewDoc,
	) => DrillRowsSource
	drillable?: boolean
}

export function makeChartRead(source: ChartSource, context?: ChartReadContext) {
	const current = computed(() => unref(source.doc))

	function filterContext(): DashboardFilterContext | undefined {
		return context?.filterContext(current.value.name)
	}

	const answered = shallowRef<{ key?: string; doc: ChartViewDoc }>()
	// The card shows the source's current chart when the rows on screen answer
	// its request, and the chart the rows came from when they do not. A display
	// option does not change the request, so it shows at once. An edit that
	// changes the rows waits for them.
	const doc = computed(() => {
		const shown = answered.value
		if (!shown || source.requestKey?.(filterContext()) === shown.key) return current.value
		return shown.doc
	})
	const result = ref<QueryResult>(emptyResult())
	const sparklineResult = ref<QueryResult>()
	const operations = ref<Operation[]>([])
	const configErrors = ref<string[]>([])
	const drillDimensions = ref<DrillDimension[]>([])
	// true by default: the builder's source never sends `can_rows`
	const drillCanRows = ref(true)
	const canFilter = ref(true)
	const canReadRows = ref(true)
	const canExport = ref(false)
	const recordLinks = ref<RecordLinks>()
	// an empty array, not undefined, so the card shows Not Permitted even when the
	// server names no doctypes
	const notPermitted = ref<string[]>()
	const scopedBy = ref<{ doctype: string; documents: string[] }[]>()
	const narrowedByPermissions = ref(false)
	// a drill sends it back, so the rows behind the number are for the date the
	// number was read, not the date of the click
	const readOn = ref<string>()
	// only the server knows this: a span is resolved while the query runs
	const comparisonRows = ref<Record<string, number | null>>()

	const ready = ref(false)
	// the author changed this chart in this tab, so the next load runs even if
	// its request is unchanged. It only marks the read: a read with no mounted
	// card has nobody waiting for rows.
	const stale = ref(false)
	const executing = ref(true)
	const failed = ref(false)
	const serverBusy = ref(false)
	// a busy server has its own state, so it leaves this empty
	const failure = ref('')
	const executedAt = ref<Date>()
	const empty = computed(() => ready.value && !result.value.rows.length)

	const executionPriority = ref<number>()

	// Only a Table pages its rows. Other chart types render all their rows as one
	// chart, so a second page would show a partial chart. Paging also needs the
	// server to allow this reader more than the chart.
	const paged = computed(() => doc.value.chart_type === 'Table' && canReadRows.value)
	const currentPage = ref(1)
	const pageSize = computed(() => (paged.value ? doc.value.config.limit || 100 : undefined))

	let currentLoad = 0
	let lastRequestKey: string | undefined
	// the request key without the page: a new request starts on page 1
	let lastQuestion: string | undefined
	// the count is cached apart from the rows, so a refresh must reach it too
	let forceCount = false

	// The rows and the values read from them go together. A load that shows no
	// rows clears all of them: a comparison row kept past its rows points at a
	// row that is gone.
	function clearChart() {
		answered.value = undefined
		result.value = emptyResult()
		sparklineResult.value = undefined
		comparisonRows.value = undefined
	}

	async function load(force = false) {
		const question = source.requestKey?.(filterContext())
		const sameQuestion = question === lastQuestion
		if (!sameQuestion) currentPage.value = 1
		lastQuestion = question
		const requestKey = question === undefined ? undefined : `${currentPage.value}:${question}`
		if (!force && !stale.value && requestKey !== undefined && requestKey === lastRequestKey)
			return
		lastRequestKey = requestKey
		if (force || stale.value) forceCount = true
		// a count belongs to the request, not the page, so it is kept until a
		// refresh runs it again
		const totalRowCount =
			sameQuestion && !force && !stale.value ? result.value.totalRowCount : 0
		stale.value = false

		executing.value = true
		failed.value = false
		serverBusy.value = false
		failure.value = ''
		notPermitted.value = undefined
		scopedBy.value = undefined
		narrowedByPermissions.value = false

		const token = ++currentLoad
		const isStale = () => token !== currentLoad

		// the rows that come back answer this copy, not later edits
		const asked = copy(current.value)
		// fetch the chart only while no rows are shown. Over rows, it would be a
		// config they do not answer
		const docLoad = answered.value ? undefined : source.fetchDoc?.()
		// Every card on a dashboard loads at once, and the server's query limiter
		// refuses the extra ones with a 503 instead of queueing them. That is not
		// an error: the card waits its turn on the queue the query builder uses,
		// and tries again. A real failure is not retried and reaches the card at
		// once.
		const page = currentPage.value
		const dataLoad = scheduleQueryExecution(
			() => source.fetchData(force, filterContext(), page),
			{
				isStale,
				priority: executionPriority.value,
			},
		)

		try {
			const placeholder = await docLoad
			if (isStale()) return
			if (placeholder && !answered.value) source.takeChartDoc?.(placeholder)

			const response = await dataLoad
			if (isStale()) return
			if (!response) throw new Error(__('This chart could not be loaded'))

			if (response.not_permitted) {
				notPermitted.value = response.not_permitted.doctypes || []
				clearChart()
				ready.value = true
				return
			}

			configErrors.value = response.errors || []
			// a half-configured chart is normal in the builder, and the old rows no
			// longer match the config on screen
			if (configErrors.value.length) {
				clearChart()
				return
			}

			if (response.chart) source.takeChartDoc?.(response.chart)
			// the server ran a chart this source does not hold (the saved one, for a
			// builder user who may not write it), so that chart is shown
			const substituted = Boolean(response.chart && !source.takeChartDoc)
			const chartDoc = substituted
				? { ...asked, ...normalizedChartDoc(response.chart!) }
				: response.chart
				  ? copy(current.value)
				  : { ...asked, modified: response.modified }

			// a hidden currency column stays in each row and is read by name. Only
			// the column list drops it
			Object.assign(session.site.currency_symbols, response.currency_symbols || {})
			const rows = {
				...emptyResult(),
				columns: withoutHidden(response.columns),
				rows: response.rows || [],
			}
			result.value = {
				...rows,
				executedSQL: response.sql || '',
				// The period column comes back without a granularity, because the
				// rows are grouped by span, not by grain. The config says how long a
				// span is, so it labels them.
				formattedRows: labelWindowRows(
					formatResultRows(rows, response.granularity || {}),
					chartDoc.chart_type,
					chartDoc.config,
				),
				columnOptions: rows.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
					query: '',
					data_type: column.type,
				})),
				// the page length is not the row count: a pager that took it for one
				// would stop at page 1. Only `fetchResultCount` sets it.
				totalRowCount,
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
			drillDimensions.value = response.drill?.dimensions || []
			drillCanRows.value = response.drill?.can_rows !== false
			canFilter.value = response.can_filter !== false
			canReadRows.value = response.can_read_rows !== false
			canExport.value = Boolean(response.can_export)
			recordLinks.value = response.record_links
			comparisonRows.value = response.comparison_rows
			scopedBy.value = response.user_permissions
			narrowedByPermissions.value = Boolean(response.narrowed_by_permissions)
			readOn.value = response.read_on
			executedAt.value = result.value.lastExecutedAt
			answered.value = { key: substituted ? undefined : question, doc: chartDoc }
			ready.value = true
		} catch (error) {
			// a load that a newer one replaced is not a failure. If it was still
			// queued, it left the queue without using a slot
			if (isStale()) return
			// no rows on screen answer this request, so the same load again is not
			// a repeat
			lastRequestKey = undefined
			serverBusy.value = isServerBusyError(error)
			failure.value = serverBusy.value ? '' : getErrorMessage(error)
			failed.value = true
			clearChart()
		} finally {
			if (!isStale()) executing.value = false
		}
	}

	function goToPage(page: number) {
		if (!paged.value || page < 1) return
		currentPage.value = page
		return load()
	}

	async function fetchResultCount() {
		if (!source.fetchCount) return
		const force = forceCount
		forceCount = false
		result.value.totalRowCount = await source.fetchCount(filterContext(), force)
	}

	const fetchExport = source.fetchExport
	const download = fetchExport
		? useResultExport(
				(format) => fetchExport(format, filterContext()),
				() => doc.value.title,
		  )
		: undefined

	// The card knows the chart a click is read against and the dimensions a
	// breakdown may use. The source knows the endpoint. Only this store holds
	// both. A click is read off the chart on screen, so the drill uses that chart,
	// even while an edit waits for its rows.
	const drillSubject = computed<DrillSubject>(() => {
		const rendered = doc.value
		return {
			chart: { chart_type: rendered.chart_type as ChartType, config: rendered.config },
			title: rendered.title,
			dimensions: drillDimensions.value,
			canRows: drillCanRows.value,
			readOn: readOn.value,
			// the version of the rows. The document being edited does not hold it
			modified: answered.value?.doc.modified,
			fetch: (levels) => source.fetchDrillData(levels, filterContext(), rendered),
			rows: source.rowsSource
				? (levels: DrillLevel[]) => source.rowsSource!(levels, filterContext(), rendered)
				: undefined,
		}
	})

	const drillable = source.drillable ?? true

	return reactive({
		doc,
		drillable,
		result,
		sparklineResult,
		currentOperations: operations,
		configErrors,
		drillDimensions,
		drillCanRows,
		canFilter,
		recordLinks,
		comparisonRows,
		notPermitted,
		scopedBy,
		narrowedByPermissions,
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

		currentPage,
		pageSize,
		goToPage: computed(() => (paged.value ? goToPage : undefined)),
		fetchResultCount: computed(() =>
			paged.value && source.fetchCount ? fetchResultCount : undefined,
		),
		downloading: download ? download.downloading : false,
		exportResults: computed(() => (canExport.value ? download?.exportResults : undefined)),
		cancelDownload: download?.cancelDownload,

		load,
	})
}

export type ChartRead = ReturnType<typeof makeChartRead>

// One read per chart, per context, per source. The cards of one dashboard share
// rows, a second dashboard that shows the chart holds its own, and the builder's
// preview is another read. Both sources cache here, because an edit makes the
// chart stale, not one read.
const reads = new Map<string, { chart: string; read: ChartRead }>()

/**
 * The key is built here, not passed in. A caller's key that disagrees with
 * `chart_name` would file the read where `invalidateChart` cannot find it.
 */
export function cachedChartRead(
	source: ChartSourceName,
	chart_name: string,
	context: ChartReadContext | undefined,
	make: () => ChartRead,
): ChartRead {
	const key = chartReadKey(source, chart_name, context)
	const existing = reads.get(key)
	if (existing) return existing.read

	const read = make()
	reads.set(key, { chart: chart_name, read })
	return read
}

/**
 * A read made before the chart is saved is keyed on `new-chart-<id>`, and every
 * invalidation after the insert uses the real name. Without this the stale mark
 * finds nothing, and the card runs the query again.
 */
export function renameChartViews(from: string, to: string) {
	if (!from || !to || from === to) return
	for (const [key, entry] of [...reads]) {
		if (entry.chart !== from) continue
		reads.delete(key)
		reads.set(`${key.slice(0, key.length - from.length)}${to}`, { chart: to, read: entry.read })
	}
}

function withoutHidden(columns?: QueryResultColumn[]): QueryResultColumn[] {
	return (columns || []).filter((column) => !column.hidden)
}

/**
 * A chart edited in the builder is the same chart the dashboard beside it
 * shows. That read would send the same request as before, so a plain load would
 * skip it as a repeat. The mark lets it through.
 *
 * Reads are marked, not run, because they outlive the cards that made them.
 * Running each one would send a query for every dashboard nobody is looking at.
 * A card that mounts loads its read and finds the mark.
 */
export function invalidateChart(chart_name: string) {
	reads.forEach((entry) => {
		if (entry.chart === chart_name) entry.read.stale = true
	})
}

/**
 * The server decides what runs from the chart name, so nothing a reader sends
 * can widen what they see, and no operations come back.
 *
 * `chartDoc` is the chart document, when the caller already has it. A dashboard
 * returns every chart on it, so its cards need no second request.
 */
export function useChartView(
	chart_name: string,
	context?: ChartReadContext,
	chartDoc?: ChartViewDoc,
) {
	// A read outlives the page that made it and keeps the chart its rows ran as.
	// A `chartDoc` passed later is ignored: over rows, it would be a config they do
	// not answer.
	return cachedChartRead('saved', chart_name, context, () =>
		makeSavedChartView(chart_name, context, chartDoc),
	)
}

// A config from the server holds only what its owner set. The defaults the card
// reads are filled in here.
function normalizedChartDoc(chartDoc: ChartViewDoc): ChartViewDoc {
	return { ...chartDoc, config: normalizeChartConfig(chartDoc.config || {}, chartDoc.chart_type) }
}

function assignChartDoc(doc: ChartViewDoc, chartDoc: ChartViewDoc) {
	Object.assign(doc, normalizedChartDoc(chartDoc))
}

function makeSavedChartView(
	chart_name: string,
	context?: ChartReadContext,
	chartDoc?: ChartViewDoc,
) {
	const doc = reactive<ChartViewDoc>({
		name: chart_name,
		title: '',
		chart_type: '',
		config: normalizeChartConfig({}, ''),
	})

	if (chartDoc) assignChartDoc(doc, chartDoc)

	// A reader changes none of the config, so the request holds only the chart
	// name and the caller's filters. Filters go by name: the server reads the
	// filter links of the dashboard named here.
	const request = (filterContext?: DashboardFilterContext) => ({
		chart: chart_name,
		dashboard: filterContext?.dashboard,
		filters: filterContext?.filters,
		card_filters: filterContext?.cardFilters,
	})

	return makeChartRead(
		{
			doc,
			fetchDoc: chartDoc
				? undefined
				: () => call('insights.api.view.get_chart', { chart: chart_name }),
			takeChartDoc: (chart_doc) => assignChartDoc(doc, chart_doc),
			// Each reading of a Number card is its own cell, and each cell loads the
			// chart. Without a key, each one runs the same query again. The server
			// holds everything else that decides the rows (the chart's filters, its
			// query, the dashboard's filter links), so a read keeps its rows until
			// Refresh.
			requestKey: (filterContext) => stableStringify(request(filterContext)),
			fetchData: (force, filterContext, page) =>
				call('insights.api.view.get_chart_data', {
					...request(filterContext),
					force,
					page,
				}),
			fetchCount: (filterContext, force) =>
				call('insights.api.view.get_chart_count', { ...request(filterContext), force }),
			fetchExport: (format, filterContext) =>
				call('insights.api.view.download_chart_rows', {
					...request(filterContext),
					format,
				}),
			// A drill reads rows, so a guest is not allowed it. The endpoint also
			// refuses Guest.
			drillable: session.isLoggedIn,
			// card filters apply after the chart's summarize, and a drill cuts before it
			fetchDrillData: (drill_stack, filterContext) => {
				const { chart, dashboard, filters } = request(filterContext)
				return fetchViewDrillData({ chart, dashboard, filters }, drill_stack)
			},
			rowsSource: (drill_stack, filterContext) => {
				const { chart, dashboard, filters } = request(filterContext)
				const drilled = { chart, dashboard, filters }
				return {
					read: (state) => fetchViewDrillData(drilled, drill_stack, state),
					download: (state, format) =>
						downloadViewDrillRows(drilled, drill_stack, state, format),
					values: (column, search, rules) =>
						fetchViewDrillRowsValues(drilled, drill_stack, column, search, rules),
					range: (column, rules) =>
						fetchViewDrillRowsRange(drilled, drill_stack, column, rules),
				}
			},
		},
		context,
	)
}
