import type { FrappeApi } from './frappe'

/**
 * Local mirrors of the shapes the API stores.
 *
 * The suite's contract is the REST payload, not the Vue app's types. Importing
 * from `src2/types` would drag frappe-ui and the whole Vue toolchain into a
 * suite that otherwise needs only Playwright.
 */
export type Operation = Record<string, unknown>
export type ChartConfig = Record<string, unknown>
export type ChartType = 'Number' | 'Bar' | 'Line' | 'Row' | 'Donut' | 'Funnel' | 'Table'

export type SourceOperation = {
	type: 'source'
	table: { type: 'table'; data_source: string; table_name: string }
}

export type Measure = {
	measure_name: string
	column_name: string
	data_type: 'String' | 'Integer' | 'Decimal'
	aggregation: 'sum' | 'count' | 'avg' | 'min' | 'max' | 'count_distinct'
}

export type Dimension = {
	dimension_name: string
	column_name: string
	data_type: 'String' | 'Date' | 'Datetime' | 'Time'
	granularity?: string
}

export type Layout = { i: string; x: number; y: number; w: number; h: number }
export type DashboardChartItem = { type: 'chart'; chart: string; layout: Layout }

export const DOCTYPE = {
	WORKBOOK: 'Insights Workbook',
	QUERY: 'Insights Query v3',
	CHART: 'Insights Chart v3',
	DASHBOARD: 'Insights Dashboard v3',
	DATA_SOURCE: 'Insights Data Source v3',
	TABLE: 'Insights Table v3',
	TEAM: 'Insights Team',
	USER: 'User',
} as const

export const DEMO_DATA_SOURCE = 'demo_data'

/** The tables `insights/setup/demo.py` syncs. Ticket 15 generates their rows. */
export const DEMO_TABLES = [
	'customers',
	'geolocation',
	'orderitems',
	'orderpayments',
	'orderreviews',
	'orders',
	'products',
	'sellers',
]

/** Every record the suite creates carries this prefix, so strays are findable. */
export const E2E_TITLE_PREFIX = 'e2e'

export type SeededWorkbook = { name: string; title: string }
export type SeededQuery = { name: string; title: string; workbook: string }
export type SeededChart = { name: string; title: string; workbook: string; query: string }
export type SeededDashboard = { name: string; title: string; workbook: string }

export function uniqueTitle(label: string): string {
	const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
	return `${E2E_TITLE_PREFIX} ${label} ${suffix}`
}

/**
 * Fail early when the demo Data Source is missing or unsynced.
 *
 * Generating the dataset takes long enough that no test should pay for it, so
 * the site build calls `insights.setup.setup_wizard.setup_demo_data` once and
 * this only checks the result. A test that skipped the check would fail deep
 * inside a chart assertion instead of at its first line.
 */
export async function assertDemoData(api: FrappeApi): Promise<void> {
	if (!(await api.docExists(DOCTYPE.DATA_SOURCE, DEMO_DATA_SOURCE))) {
		throw new Error(`Data Source "${DEMO_DATA_SOURCE}" is missing. Run the demo setup first.`)
	}

	const tables = await api.getList<{ table: string }>(DOCTYPE.TABLE, {
		fields: ['table'],
		filters: { data_source: DEMO_DATA_SOURCE },
		limit: 0,
	})
	const found = new Set(tables.map((row) => row.table))
	const missing = DEMO_TABLES.filter((table) => !found.has(table))
	if (missing.length) {
		throw new Error(
			`Data Source "${DEMO_DATA_SOURCE}" is missing tables: ${missing.join(', ')}`,
		)
	}
}

export async function createWorkbook(api: FrappeApi, title?: string): Promise<SeededWorkbook> {
	const workbookTitle = title || uniqueTitle('Workbook')
	const doc = await api.createDoc<{ name: string }>(DOCTYPE.WORKBOOK, { title: workbookTitle })
	return { name: doc.name, title: workbookTitle }
}

/**
 * Delete a Workbook and everything in it.
 *
 * `Insights Workbook.on_trash` cascades to its queries, charts, dashboards and
 * folders, so one delete tears down a whole fixture.
 */
export async function deleteWorkbook(api: FrappeApi, name: string): Promise<void> {
	await api.deleteDoc(DOCTYPE.WORKBOOK, name).catch(() => {})
}

export function sourceOperation(tableName: string, dataSource = DEMO_DATA_SOURCE): SourceOperation {
	return {
		type: 'source',
		table: { type: 'table', data_source: dataSource, table_name: tableName },
	}
}

export async function createQuery(
	api: FrappeApi,
	options: {
		workbook: string
		title?: string
		operations?: Operation[]
		table?: string
		dataSource?: string
	},
): Promise<SeededQuery> {
	const title = options.title || uniqueTitle('Query')
	const operations = options.operations || [
		sourceOperation(options.table || 'orders', options.dataSource),
	]
	const doc = await api.createDoc<{ name: string }>(DOCTYPE.QUERY, {
		title,
		workbook: options.workbook,
		use_live_connection: 1,
		is_builder_query: 1,
		operations,
	})
	return { name: doc.name, title, workbook: options.workbook }
}

/** A row count split by a dimension. The smallest configuration a Chart renders. */
export function countByConfig(dimension: Dimension): ChartConfig {
	const rowCount: Measure = {
		measure_name: 'count_of_rows',
		column_name: 'count',
		data_type: 'Integer',
		aggregation: 'count',
	}
	return {
		x_axis: { dimension },
		y_axis: { series: [{ measure: rowCount }] },
		order_by: [],
		limit: 100,
	}
}

export const ORDER_STATUS_DIMENSION: Dimension = {
	dimension_name: 'order_status',
	column_name: 'order_status',
	data_type: 'String',
}

export async function createChart(
	api: FrappeApi,
	options: {
		workbook: string
		query: string
		title?: string
		chartType?: ChartType
		config?: ChartConfig
	},
): Promise<SeededChart> {
	const title = options.title || uniqueTitle('Chart')
	const doc = await api.createDoc<{ name: string }>(DOCTYPE.CHART, {
		title,
		workbook: options.workbook,
		query: options.query,
		chart_type: options.chartType || 'Bar',
		config: options.config || countByConfig(ORDER_STATUS_DIMENSION),
	})
	return { name: doc.name, title, workbook: options.workbook, query: options.query }
}

export async function createDashboard(
	api: FrappeApi,
	options: { workbook: string; title?: string; charts?: string[] },
): Promise<SeededDashboard> {
	const title = options.title || uniqueTitle('Dashboard')
	const items: DashboardChartItem[] = (options.charts || []).map((chart, index) => ({
		type: 'chart',
		chart,
		layout: { i: `chart-${index}`, x: 0, y: index * 8, w: 10, h: 8 },
	}))
	const doc = await api.createDoc<{ name: string }>(DOCTYPE.DASHBOARD, {
		title,
		workbook: options.workbook,
		items,
	})
	return { name: doc.name, title, workbook: options.workbook }
}
