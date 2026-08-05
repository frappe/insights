// The island's data path: `insights.api.viewer`, and nothing else.
//
// An island mounts for a desk user who may hold no Insights role, so it names
// the content and the server decides what runs — unlike the SPA, which reaches
// documents through role-gated resources and rebuilds each chart's query in the
// browser. The query behind a chart never comes back.

import { call } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import type { Chart } from '../charts/chart'
import { normalizeChartConfig } from '../charts/helpers'
import { EMPTY_RESULT, formatResultRows } from '../query/helpers'
import type { Layout } from '../types/workbook.types'
import type { FilterOperator, FilterType, FilterValue, QueryResult } from '../types/query.types'

export type ViewerDashboardItem = {
	type: 'chart' | 'text' | 'filter'
	layout: Layout
	chart?: string
	text?: string
	filter_name?: string
	filter_type?: FilterType
	default_operator?: FilterOperator
	default_value?: FilterValue
}

export type ViewerDashboard = {
	name: string
	slug: string
	title: string
	items: ViewerDashboardItem[]
	vertical_compact_layout: boolean
	modified: string
	can_edit: boolean
	can_duplicate: boolean
}

// dashboard filter state, keyed by filter name. Which query a filter lands on is
// the server's business — the links that say so never reach a viewer.
export type ViewerFilters = Record<string, { operator: FilterOperator; value: FilterValue }>

export function fetchDashboard(dashboard: string): Promise<ViewerDashboard> {
	return call('insights.api.viewer.get_dashboard', { dashboard })
}

export type ViewerChartOptions = {
	// the dashboard the chart is being viewed on, if any. It carries the chart's
	// audience and is what makes filter state routable.
	dashboard?: string
	filters?: () => ViewerFilters | undefined
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

	async function load(force = false) {
		executing.value = true
		failed.value = false

		// config and rows are two round trips on purpose: the card draws its
		// frame from the first and fills in with the second
		const config = call('insights.api.viewer.get_chart', {
			chart: reference,
			dashboard: options.dashboard,
		})
		const data = call('insights.api.viewer.get_chart_data', {
			chart: reference,
			dashboard: options.dashboard,
			filters: options.filters?.(),
			force,
		})

		try {
			const chart_doc = await config
			Object.assign(doc, chart_doc)
			doc.config = normalizeChartConfig(chart_doc.config || {}, chart_doc.chart_type)

			const response = await data
			const rows = { ...EMPTY_RESULT, columns: response.columns, rows: response.rows }
			result.value = {
				...rows,
				formattedRows: formatResultRows(rows, response.granularity || {}),
				totalRowCount: response.rows.length,
				timeTaken: response.time_taken,
				lastExecutedAt: new Date(response.executed_at),
			}
			loaded.value = true
		} catch (error) {
			failed.value = true
			result.value = { ...EMPTY_RESULT }
		} finally {
			executing.value = false
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

	return { chart, load, loaded, executing, failed }
}

export type ViewerChart = ReturnType<typeof useViewerChart>
