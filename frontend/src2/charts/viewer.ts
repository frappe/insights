// One chart as a viewer reads it: the config it draws itself from, and the rows
// the server ran for it. Both come from `insights.api.viewer`, which takes the
// chart by name — a reader never says what query to run.

import { call } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import type { Chart } from './chart'
import { normalizeChartConfig } from './helpers'
import type { ViewerFilters } from '../dashboard/viewer'
import { scheduleQueryExecution } from '../query/execution_queue'
import { EMPTY_RESULT, formatResultRows } from '../query/helpers'
import type { QueryResult } from '../types/query.types'

export type ViewerChartOptions = {
	// the dashboard the chart is being viewed on, if any. It carries the chart's
	// audience and is what makes filter state routable.
	dashboard?: string
	filters?: () => ViewerFilters | undefined
	// where this card sits on the grid, so the queue serves the top of the page
	// before the bottom
	priority?: number
}

export function useViewerChart(reference: string, options: ViewerChartOptions = {}) {
	const doc = reactive({
		name: reference,
		title: '',
		chart_type: '',
		config: normalizeChartConfig({}, ''),
		can_edit: false,
	})

	const result = ref<QueryResult>({ ...EMPTY_RESULT })
	const loaded = ref(false)
	const executing = ref(true)
	const failed = ref(false)
	// when the rows on screen were produced. It is the card that knows, so the
	// page's freshness stamp is read off the cards
	const executedAt = ref<Date>()
	const empty = computed(() => loaded.value && !result.value.rows.length)

	let currentLoad = 0

	async function load(force = false) {
		executing.value = true
		failed.value = false

		const token = ++currentLoad
		const isStale = () => token !== currentLoad

		// config and rows are two round trips on purpose: the card draws its
		// frame from the first and fills in with the second
		const config = call('insights.api.viewer.get_chart', {
			chart: reference,
			dashboard: options.dashboard,
		})
		// Every card on a dashboard fires at once, and the server's query limiter
		// turns the surplus away with a 503 rather than queueing them. Nothing is
		// wrong when that happens — the card waits its turn and asks again, on the
		// same queue the builder's charts use. A real failure is not retried and
		// reaches the card immediately.
		const data = scheduleQueryExecution(
			() =>
				call('insights.api.viewer.get_chart_data', {
					chart: reference,
					dashboard: options.dashboard,
					filters: options.filters?.(),
					force,
				}),
			{ isStale, priority: options.priority },
		)

		try {
			const chart_doc = await config
			if (isStale()) return
			Object.assign(doc, chart_doc)
			doc.config = normalizeChartConfig(chart_doc.config || {}, chart_doc.chart_type)

			const response = await data
			if (isStale()) return
			const rows = { ...EMPTY_RESULT, columns: response.columns, rows: response.rows }
			result.value = {
				...rows,
				formattedRows: formatResultRows(rows, response.granularity || {}),
				totalRowCount: response.rows.length,
				timeTaken: response.time_taken,
				lastExecutedAt: new Date(response.executed_at),
			}
			executedAt.value = result.value.lastExecutedAt
			loaded.value = true
		} catch (error) {
			// a load a newer one has superseded is not a failure — and while it
			// waited in the queue it dropped out rather than spending a slot on a
			// result nobody is waiting for
			if (isStale()) return
			failed.value = true
			result.value = { ...EMPTY_RESULT }
		} finally {
			if (!isStale()) executing.value = false
		}
	}

	// The renderer takes a `Chart` — the builder's aggregate, a store with a
	// document it can save and a query it can re-run. A viewer holds the same
	// picture with that whole half absent, so the missing pieces answer inertly
	// rather than being left undefined for the renderer to trip over. Anything
	// that would re-shape the data is a no-op: re-shaping is a query, and the
	// server owns the query.
	const chart = reactive({
		doc,
		isloaded: loaded,
		isConfigValid: true,
		refresh: (force?: boolean) => load(force),
		dataQuery: reactive({
			name: reference,
			result,
			isloaded: loaded,
			islocal: false,
			executing,
			isServerBusy: false,
			downloading: false,
			currentOperations: [],
			currentPage: 1,
			// what came back is the whole of it, so the table filters and paginates
			// over the rows it holds instead of asking for a page it cannot get
			pageSize: computed(() => result.value.rows.length + 1),
			adhocFilters: undefined,
			getDrillDownQuery: async () => null,
			addOrderBy: () => {},
			removeOrderBy: () => {},
			fetchResultCount: () => {},
			goToPage: () => {},
			renameColumn: () => {},
			cancelDownload: () => {},
		}),
	}) as unknown as Chart

	return { chart, load, loaded, executing, failed, empty, executedAt }
}

export type ViewerChart = ReturnType<typeof useViewerChart>
