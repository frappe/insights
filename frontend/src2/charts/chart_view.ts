// One chart as anything that draws it reads it: the config it draws itself from,
// and the rows the server ran for it.
//
// Two sources fill it. A saved chart names itself to `insights.api.view`, which
// answers rendering and nothing else — a reader never says what query to run,
// and never learns what ran. The builder has no saved chart to name, so it sends
// the config it is editing to `insights.api.authoring` and gets the derived
// operations back with the rows. That endpoint is closed to anyone without an
// Insights role.
//
// Above the fetch the two are the same store: the same result, the same
// loading, failure and empty states, the same freshness stamp, the same
// priority-queued execution.
//
// A read holds the chart and its rows as one snapshot. Nothing replaces it but
// a load that brings both, so a card never draws a definition over rows it did
// not produce.

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
	filters?: FilterValues
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
// these, which is what lets the preview source read straight off what is being edited
export type ChartViewDoc = {
	name: string
	title: string
	chart_type: string
	config: InsightsChartv3['config']
	can_write?: boolean
	// the version of the chart drawn, which a drill carries back
	modified?: string
	// the query the builder's own document reads. A view's frame never names it
	query?: string
}

type ChartDataResponse = {
	// the chart these rows were computed from, where the source names a saved
	// one. The builder's source sent its own, so it needs none back
	chart?: ChartViewDoc
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
	// what a segment click may break the card down by. It comes with the rows
	// because a menu that has to ask first puts a round trip in the one place
	// latency is felt — between the click and the menu.
	// `can_rows` says whether this reader may have the rows behind a segment and
	// not only a picture of them. The server decides it, so the menu draws the
	// act only where it leads somewhere.
	drill?: { dimensions: DrillDimension[]; can_rows?: boolean }
	// whether this reader may put a filter of their own on the card. The server
	// refuses one on a chart run as its owner, so the card offers it only here
	can_filter?: boolean
	// whether this reader may have more than the picture: a page past the first
	// and the count. Absent means yes, as for `drill.can_rows`
	can_read_rows?: boolean
	// whether this reader may take the rows away as a file
	can_export?: boolean
	// which row answers each of a number card's comparisons, keyed by the source
	// that asks it. A row named `null` was asked for and came back empty. A
	// source left out is one the card's period cannot be asked at all
	comparison_rows?: Record<string, number | null>
	// which result columns name a desk document, when the rows are documents. A
	// grid draws them as links. Every other chart type ignores them.
	record_links?: RecordLinks
	// the chart reads a table or a permlevel column this reader may not read, so
	// it did not run. The doctypes are what they would need read on. An answer,
	// not a failure: there is nothing to retry.
	not_permitted?: NotPermitted
	// the reader's own User Permissions that narrowed these rows, so the card can
	// say the number is theirs and not the whole one
	user_permissions?: { doctype: string; documents: string[] }[]
	// a team's Table Restriction, or a column blanked on the rows only desk
	// admits, narrowed these rows and names nothing
	narrowed_by_permissions?: boolean
	// the symbol of every currency code the rows carry, so any code prints
	currency_symbols?: Session['site']['currency_symbols']
	// the day this card's spans resolved against. A span is stored unresolved,
	// so only the card can say which stretch its number counted
	drawn_on?: string
	// the builder's answer: the version of the saved chart its rows ran as
	modified?: string
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
}

/** A read is one chart, as one source's surface reads it. */
function chartReadKey(source: ChartSourceName, chart_name: string, surface?: ChartReadSurface) {
	return `${source}:${surface?.id || ''}:${chart_name}`
}

/** Which source the rows came from: the saved chart's, or the builder's. */
export type ChartSourceName = 'saved' | 'preview'

export type ChartSource = {
	// the chart as the source holds it now. A card draws it only while the rows
	// on screen answer it
	doc: ChartViewDoc | ComputedRef<ChartViewDoc>
	// a frame to draw before any rows, for a saved chart nothing handed one over
	// for. The preview source already holds the document it is editing.
	fetchDoc?: () => Promise<ChartViewDoc | undefined>
	// take the frame an answer carried as the chart the source now holds
	takeFrame?: (frame: ChartViewDoc) => void
	fetchData: (
		force: boolean,
		filterContext: DashboardFilterContext | undefined,
		page: number,
	) => Promise<ChartDataResponse | undefined>
	// how many rows the pages are cut from, under the same filters
	fetchCount?: (
		filterContext: DashboardFilterContext | undefined,
		force: boolean,
	) => Promise<number>
	// every one of those rows as a file
	fetchExport?: (format: string, filterContext?: DashboardFilterContext) => Promise<string>
	// What this source would ask for, as a string. A load that would ask the same
	// question again is dropped before it starts: the rows on screen are already
	// its answer, and running it puts the card through its loading state for a
	// picture that does not change. A source that leaves it out runs every load.
	requestKey?: (filterContext?: DashboardFilterContext) => string
	// one level of a drill, through this source's endpoint. The stack the dialog
	// holds is the whole request, cut from `drawn`, the chart the card is
	// drawing. No operations cross either way, except back out of the authoring
	// endpoint.
	fetchDrillData: (
		levels: DrillLevel[],
		filterContext: DashboardFilterContext | undefined,
		drawn: ChartViewDoc,
	) => Promise<DrillLevelData>
	// The rows level again, read the way the reader asked: sorted, narrowed by a
	// find term, at a page — and the same cut as a file.
	rowsSource?: (
		levels: DrillLevel[],
		filterContext: DashboardFilterContext | undefined,
		drawn: ChartViewDoc,
	) => DrillRowsSource
	// whether this source answers a drill at all. A card draws the affordance only
	// where it leads somewhere, the way a table's sort is drawn only where the
	// surface holds the config.
	drillable?: boolean
}

export function makeChartRead(
	source: ChartSource,
	// the surface this read belongs to: what it narrows the chart by, asked on
	// every load
	surface?: ChartReadSurface,
) {
	// the preview source hands over a ref to the document it is editing
	const current = computed(() => unref(source.doc))

	function filterContext(): DashboardFilterContext | undefined {
		return surface?.filterContext(current.value.name)
	}

	// the chart the rows on screen were computed from, and the request that
	// asked for them. Absent while no rows are drawn.
	const answered = shallowRef<{ key?: string; doc: ChartViewDoc }>()
	// What the card draws: the chart as the source holds it wherever the rows on
	// screen answer it, and the chart they were computed from where they do not.
	// A display option leaves the request alone, so it is drawn at once; an edit
	// that decides the rows waits for them.
	const doc = computed(() => {
		const shown = answered.value
		if (!shown || source.requestKey?.(filterContext()) === shown.key) return current.value
		return shown.doc
	})
	const result = ref<QueryResult>(emptyResult())
	// the series a span card's sparkline is drawn from, when the server ran
	// one for it
	const sparklineResult = ref<QueryResult>()
	const operations = ref<Operation[]>([])
	// why the chart cannot be drawn yet, as the server read the config
	const configErrors = ref<string[]>([])
	const drillDimensions = ref<DrillDimension[]>([])
	// true until a server says otherwise: the builder's source answers no such
	// key, and always reads its own rows
	const drillCanRows = ref(true)
	const canFilter = ref(true)
	const canReadRows = ref(true)
	const canExport = ref(false)
	const recordLinks = ref<RecordLinks>()
	// the doctypes a Not Permitted card names. Empty array and not null, so the
	// card can say it plainly even when the server named none.
	const notPermitted = ref<string[]>()
	// what narrowed the rows on screen, as the server applied it
	const scopedBy = ref<{ doctype: string; documents: string[] }[]>()
	const narrowedByPermissions = ref(false)
	// the day the spans this card reads resolved against, as the server named
	// it. A drill carries it back, so what is behind the number is cut for the
	// day the number was read and not for the day of the click
	const drawnOn = ref<string>()
	// which row a number card's comparison is measured against, as the server
	// named it. Only the server can say: a span is resolved while the query runs
	const comparisonRows = ref<Record<string, number | null>>()

	const ready = ref(false)
	// the author changed the chart behind this read in this tab, so the next load
	// runs whether or not the request it would send has changed. It is a mark and
	// not a run: a read whose surface is unmounted has nobody waiting for rows.
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

	// One page is one request, as long as the chart's own limit. Only a Table
	// draws a page: every other chart draws its rows as one picture, so a later
	// page would redraw it over rows it does not state. And only for a reader the
	// server says may have more than the picture.
	const paged = computed(() => doc.value.chart_type === 'Table' && canReadRows.value)
	const currentPage = ref(1)
	const pageSize = computed(() => (paged.value ? doc.value.config.limit || 100 : undefined))

	let currentLoad = 0
	// the question the rows on screen answer, so the same one is not asked twice
	let lastRequestKey: string | undefined
	// the same, less the page: a new question starts on its first page
	let lastQuestion: string | undefined
	// the count caches apart from the rows, so a refresh has to reach it too
	let forceCount = false

	// The rows and what is read off them are one picture, so a load that draws
	// none leaves none: a comparison pairing kept past its rows names a row that
	// is no longer there.
	function clearPicture() {
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
		// a count answers the question and not the page, until a refresh re-runs it
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

		// the chart as asked, which is what the rows coming back answer
		const asked = copy(current.value)
		// a frame is only a placeholder where no rows are drawn: over rows, it
		// would be a definition they do not answer
		const docLoad = answered.value ? undefined : source.fetchDoc?.()
		// Every card on a dashboard fires at once, and the server's query limiter
		// turns the surplus away with a 503 rather than queueing them. Nothing is
		// wrong when that happens — the card waits its turn and asks again, on the
		// same queue the query builder uses. A real failure is not retried and
		// reaches the card immediately.
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
			if (placeholder && !answered.value) source.takeFrame?.(placeholder)

			const response = await dataLoad
			if (isStale()) return
			// a source that answers nothing answers nothing about the chart either:
			// the card has no picture and no reason it has none, so it fails and
			// the reader can ask again
			if (!response) throw new Error(__('This chart could not be loaded'))

			// the card names what it needs where the picture would be, and holds
			// its place in the grid. Nothing was run, so there is nothing to draw.
			if (response.not_permitted) {
				notPermitted.value = response.not_permitted.doctypes || []
				clearPicture()
				ready.value = true
				return
			}

			configErrors.value = response.errors || []
			// a half-configured chart is the builder's normal state, and the rows
			// it last drew no longer answer the config on screen. The card says
			// what is missing where the picture was.
			if (configErrors.value.length) {
				clearPicture()
				return
			}

			if (response.chart) source.takeFrame?.(response.chart)
			// the server ran a chart this source does not hold - the stored one, for
			// a builder whose reader may not write it - so that is what is drawn
			const substituted = Boolean(response.chart && !source.takeFrame)
			const frame = substituted
				? { ...asked, ...framed(response.chart!) }
				: response.chart
				  ? copy(current.value)
				  : { ...asked, modified: response.modified }

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
					frame.chart_type,
					frame.config,
				),
				columnOptions: rows.columns.map((column) => ({
					label: column.name,
					value: column.name,
					description: column.type,
					query: '',
					data_type: column.type,
				})),
				// the page's length is not the count, and a reader that takes it for
				// one stops at the first page. Only `fetchResultCount` says.
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
			drawnOn.value = response.drawn_on
			executedAt.value = result.value.lastExecutedAt
			answered.value = { key: substituted ? undefined : question, doc: frame }
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

	// Everything the drill dialog needs from this card. The card knows the shape a
	// click is read against and the candidates a breakdown may offer. The source
	// knows the endpoint. Nothing above holds both halves. A click is read off
	// the chart on screen, so that is the chart the drill is cut from, even while
	// an edit waits for its rows.
	const drillSubject = computed<DrillSubject>(() => {
		const drawn = doc.value
		return {
			chart: { chart_type: drawn.chart_type as ChartType, config: drawn.config },
			title: drawn.title,
			dimensions: drillDimensions.value,
			canRows: drillCanRows.value,
			drawnOn: drawnOn.value,
			// the rows' version, which the document being edited does not hold
			modified: answered.value?.doc.modified,
			fetch: (levels) => source.fetchDrillData(levels, filterContext(), drawn),
			rows: source.rowsSource
				? (levels: DrillLevel[]) => source.rowsSource!(levels, filterContext(), drawn)
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
		// a surface pages a read that offers these, so a chart that is not paged offers none
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

// One read per chart per surface per source: the cards of one shared dashboard
// draw from the same rows, a second dashboard reading the same chart holds its
// own, and the builder's preview of that chart is a read beside both. Both
// sources cache here, because what goes stale is the chart and not one of its
// reads.
const reads = new Map<string, { chart: string; read: ChartRead }>()

/**
 * The read behind one source's surface, made on the first caller that asks for it.
 *
 * The key is built here rather than passed in: it is what tells one read from
 * another, and a caller free to hand over a key that disagrees with the chart
 * beside it can file a read where nothing invalidating that chart will find it.
 */
export function cachedChartRead(
	source: ChartSourceName,
	chart_name: string,
	surface: ChartReadSurface | undefined,
	make: () => ChartRead,
): ChartRead {
	const key = chartReadKey(source, chart_name, surface)
	const existing = reads.get(key)
	if (existing) return existing.read

	const read = make()
	reads.set(key, { chart: chart_name, read })
	return read
}

/**
 * Re-file a chart's reads under the name its insert gave it.
 *
 * A read made while the chart was unsaved is keyed on `new-chart-<id>`, and
 * every invalidation after the insert names the real chart. Without this the
 * mark reaches nothing, and the card that drew the rows runs the query again.
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
export function invalidateChart(chart_name: string) {
	reads.forEach((entry) => {
		if (entry.chart === chart_name) entry.read.stale = true
	})
}

/**
 * The view source: a saved chart, named to the view endpoints.
 *
 * Every view surface comes through here — the public link, the app's dashboard
 * page and the desk island alike. What runs is decided from the name, so nothing
 * a reader sends can widen what they see, and no operations come back.
 *
 * `frame` is the chart's own frame, where the surface already holds it. A
 * dashboard answers with every chart on it, so a card on one needs no second
 * round trip.
 */
export function useChartView(chart_name: string, surface?: ChartReadSurface, frame?: ChartViewDoc) {
	// A read outlives the page that made it, and holds the frame it drew its rows
	// with. A frame handed over later is a placeholder for a read that has none:
	// over rows, it would be a definition they do not answer.
	return cachedChartRead('saved', chart_name, surface, () =>
		makeSavedChartView(chart_name, surface, frame),
	)
}

// A config off the wire holds only what its owner set. The slots the card draws
// from are filled in here, wherever the frame came from.
function framed(frame: ChartViewDoc): ChartViewDoc {
	return { ...frame, config: normalizeChartConfig(frame.config || {}, frame.chart_type) }
}

function assignFrame(doc: ChartViewDoc, frame: ChartViewDoc) {
	Object.assign(doc, framed(frame))
}

function makeSavedChartView(chart_name: string, surface?: ChartReadSurface, frame?: ChartViewDoc) {
	const doc = reactive<ChartViewDoc>({
		name: chart_name,
		title: '',
		chart_type: '',
		config: normalizeChartConfig({}, ''),
	})

	if (frame) assignFrame(doc, frame)

	// A reader changes none of the config, so what the server is asked for is the
	// chart's name and the narrowing the surface put on it. Filter state goes by
	// filter name: the server reads the links of the dashboard named here.
	const request = (filterContext?: DashboardFilterContext) => ({
		chart: chart_name,
		dashboard: filterContext?.dashboard,
		filters: filterContext?.filters,
		card_filters: filterContext?.cardFilters,
	})

	return makeChartRead(
		{
			doc,
			// only where the surface could not hand the frame over
			fetchDoc: frame
				? undefined
				: () => call('insights.api.view.get_chart', { chart: chart_name }),
			takeFrame: (chart_doc) => assignFrame(doc, chart_doc),
			// A number card is one cell per reading, and every cell loads the chart
			// it draws. Without a key each of them is a separate execution of the one
			// query.
			// A reader never says what runs, so the request alone names the chart and
			// the surface's narrowing. What else decides the rows — the chart's own
			// filters, the query behind it, where the grid routes a filter — is held
			// by the server, and a read keeps what it drew until Refresh asks again.
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
			// Drilling is row exploration, and an anonymous reader is not offered it
			// — a public chart stays a picture. The endpoint refuses Guest as well.
			drillable: session.isLoggedIn,
			// a card filter lands after the chart's summarize, where a drill does not go
			fetchDrillData: (drill_stack, filterContext) => {
				const { chart, dashboard, filters } = request(filterContext)
				return fetchViewDrillData({ chart, dashboard, filters }, drill_stack)
			},
			// the reading is the reader's and the cut is the server's, so all four
			// of these name the same walk and differ only in what comes back
			rowsSource: (drill_stack, filterContext) => {
				const { chart, dashboard, filters } = request(filterContext)
				const drilled = { chart, dashboard, filters }
				return {
					read: (reading) => fetchViewDrillData(drilled, drill_stack, reading),
					download: (reading, format) =>
						downloadViewDrillRows(drilled, drill_stack, reading, format),
					values: (column, search, rules) =>
						fetchViewDrillRowsValues(drilled, drill_stack, column, search, rules),
					range: (column, rules) =>
						fetchViewDrillRowsRange(drilled, drill_stack, column, rules),
				}
			},
		},
		surface,
	)
}
