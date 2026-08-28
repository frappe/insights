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
export type DashboardFilterItem = {
	type: 'filter'
	filter_name: string
	filter_type: 'String' | 'Number' | 'Date'
	links: Record<string, string>
	layout: Layout
}

/** A Dashboard filter routed at one Chart's column. */
export type SeededFilter = { name: string; chart: string; query: string; column: string }

export const DOCTYPE = {
	WORKBOOK: 'Insights Workbook',
	QUERY: 'Insights Query v3',
	CHART: 'Insights Chart v3',
	DASHBOARD: 'Insights Dashboard v3',
	DATA_SOURCE: 'Insights Data Source v3',
	TABLE: 'Insights Table v3',
	TEAM: 'Insights Team',
	SETTINGS: 'Insights Settings',
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

/** A row count split by a dimension. The smallest configuration a Bar Chart draws. */
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
	options: { workbook: string; title?: string; charts?: string[]; filters?: SeededFilter[] },
): Promise<SeededDashboard> {
	const title = options.title || uniqueTitle('Dashboard')
	const charts: DashboardChartItem[] = (options.charts || []).map((chart, index) => ({
		type: 'chart',
		chart,
		layout: { i: `chart-${index}`, x: 0, y: index * 8 + 2, w: 10, h: 8 },
	}))
	// A filter routes by a link string the dashboard parses back into a Query
	// and a column, spelled `query`.`column` with backticks. The key is the
	// Chart the filter reaches.
	const filters: DashboardFilterItem[] = (options.filters || []).map((filter, index) => ({
		type: 'filter',
		filter_name: filter.name,
		filter_type: 'String',
		links: { [filter.chart]: `\`${filter.query}\`.\`${filter.column}\`` },
		layout: { i: `filter-${index}`, x: index * 4, y: 0, w: 4, h: 2 },
	}))
	const doc = await api.createDoc<{ name: string }>(DOCTYPE.DASHBOARD, {
		title,
		workbook: options.workbook,
		items: [...filters, ...charts],
	})
	return { name: doc.name, title, workbook: options.workbook }
}

/**
 * Publishing is not a REST write.
 *
 * `is_public` and `permission_user` sit at permlevel 1, so a PUT drops them
 * without an error. `update_access` is the only way in. It is a document
 * method, so it goes through `insights.api.run_doc_method`, the same route the
 * app uses.
 */
async function runDocMethod(
	api: FrappeApi,
	doctype: string,
	name: string,
	method: string,
	args: Record<string, unknown>,
): Promise<void> {
	// The method runs on the document the request body carries, so send the
	// stored one. A dashboard checks `linked_charts` before it publishes, and a
	// stub of doctype and name alone would carry none.
	const docs = await api.getDoc(doctype, name)
	await api.callMethod('insights.api.run_doc_method', { method, docs, args })
}

/** Publish a Dashboard, so anyone with the link opens it without a login. */
export async function publishDashboard(api: FrappeApi, name: string): Promise<void> {
	await runDocMethod(api, DOCTYPE.DASHBOARD, name, 'update_access', {
		data: { is_public: 1, is_shared_with_organization: 0, people_with_access: [] },
	})
}

/** Withdraw a Dashboard, so its public link stops working. */
export async function unpublishDashboard(api: FrappeApi, name: string): Promise<void> {
	await runDocMethod(api, DOCTYPE.DASHBOARD, name, 'update_access', {
		data: { is_public: 0, is_shared_with_organization: 0, people_with_access: [] },
	})
}

/** Publish a Chart, so anyone with the link opens it without a login. */
export async function publishChart(api: FrappeApi, name: string): Promise<void> {
	await runDocMethod(api, DOCTYPE.CHART, name, 'update_access', { is_public: 1 })
}

/**
 * Grant a user access to a Workbook.
 *
 * A grant is a DocShare row, not a field on the Workbook, so a REST write
 * cannot make one. `update_share_permissions` is the route the share dialog
 * uses, and it replaces the whole user list, so pass every user the Workbook
 * should reach.
 */
export async function shareWorkbook(
	api: FrappeApi,
	name: string,
	grants: { user: string; access: 'view' | 'edit' }[],
): Promise<void> {
	await api.callMethod('insights.api.workbooks.update_share_permissions', {
		workbook_name: name,
		user_permissions: grants.map((grant) => ({
			user: grant.user,
			read: 1,
			write: grant.access === 'edit' ? 1 : 0,
		})),
	})
}

/** Whether team permission checks are on for the whole site. */
export async function getTeamPermissions(api: FrappeApi): Promise<boolean> {
	const settings = await api.getDoc<{ enable_permissions: number }>(
		DOCTYPE.SETTINGS,
		DOCTYPE.SETTINGS,
	)
	return Boolean(settings.enable_permissions)
}

/**
 * Turn team permissions on or off for the whole site.
 *
 * Without them every Insights User reaches every Data Source and Table, so a
 * flow about a denied Data Source has nothing to deny. The setting is
 * site-wide, so only the setup and teardown projects call this. A test that
 * flipped it would flip it for every worker beside it.
 */
export async function setTeamPermissions(api: FrappeApi, enabled: boolean): Promise<void> {
	await api.updateDoc(DOCTYPE.SETTINGS, DOCTYPE.SETTINGS, {
		enable_permissions: enabled ? 1 : 0,
	})
}

/** Delete a Team. Teardown for a flow that builds one through the interface. */
export async function deleteTeam(api: FrappeApi, teamName: string): Promise<void> {
	await api.callMethod('insights.api.user.delete_team', { team_name: teamName }).catch(() => {})
}

/**
 * Fill in the derived Query a Chart executes.
 *
 * The chart builder writes this. It compiles the chart config into operations,
 * puts them on the Chart's `data_query`, and the resource autosaves them. A
 * Chart seeded over REST never passes through the builder, so its `data_query`
 * holds no operations.
 *
 * A signed-in viewer never notices, because the browser sends the operations it
 * just compiled. A public execution reloads the stored document and drops the
 * caller's copy, so a published Chart whose `data_query` is empty renders
 * nothing at all.
 */
export async function buildChartDataQuery(
	api: FrappeApi,
	chart: SeededChart,
	dimension: Dimension = ORDER_STATUS_DIMENSION,
): Promise<void> {
	const doc = await api.getDoc<{ data_query: string }>(DOCTYPE.CHART, chart.name)
	await api.updateDoc(DOCTYPE.QUERY, doc.data_query, {
		use_live_connection: 1,
		operations: [
			{ type: 'source', table: { type: 'query', workbook: '', query_name: chart.query } },
			{
				type: 'summarize',
				measures: [
					{
						measure_name: 'count_of_rows',
						column_name: 'count',
						data_type: 'Integer',
						aggregation: 'count',
					},
				],
				dimensions: [dimension],
			},
		],
	})
}

/**
 * The Data Source the upload dialog writes into.
 *
 * `insights.api.get_file_data` creates it on the first upload a site ever
 * takes, so a flow that uploads finds it there whether or not it existed.
 */
export const UPLOADS_DATA_SOURCE = 'uploads'

/**
 * The Table document for a Data Source table, or null when there is none.
 *
 * `InsightsTablev3.autoname` hashes the pair, so the name carries no meaning.
 * The document keeps both halves as fields, so ask the site for it rather than
 * repeat the hash here. Teardown needs it.
 */
export async function findTableDocName(
	api: FrappeApi,
	dataSource: string,
	tableName: string,
): Promise<string | null> {
	const [table] = await api.getList<{ name: string }>(DOCTYPE.TABLE, {
		fields: ['name'],
		filters: { data_source: dataSource, table: tableName },
		limit: 1,
	})
	return table?.name ?? null
}

export type UploadedTable = { dataSource: string; table: string; file: string }

/**
 * A table name no other run holds.
 *
 * The Uploads Data Source is site-wide, so two runs that share a table name
 * race: one deletes the table document while the other is reading it. Measured,
 * once, against a second suite run on the same site.
 */
export function uniqueTableName(label: string): string {
	return `${E2E_TITLE_PREFIX}_${label}_${Math.random().toString(36).slice(2, 8)}`
}

/**
 * Seed a table in the Uploads Data Source, the way the upload dialog does.
 *
 * Two calls, the same two the dialog makes: the file goes up the normal upload
 * route, then Insights reads it into DuckDB under `tableName`. The import
 * overwrites, so a rerun replaces the table rather than adding one.
 */
export async function uploadCsvTable(
	api: FrappeApi,
	tableName: string,
	csv: string,
): Promise<UploadedTable> {
	const file = await api.uploadFile(`${tableName}-${Date.now()}.csv`, csv)
	await api.callMethod('insights.api.import_csv_data', {
		filename: file.name,
		tablename: tableName,
	})
	return { dataSource: UPLOADS_DATA_SOURCE, table: tableName, file: file.name }
}

/**
 * Drop a table's copy out of the Data Store.
 *
 * `clear_warehouse_data` drops the DuckDB table and clears `stored`, so the
 * table leaves the Data Store list. It is a document method, so it goes through
 * `run_doc_method`, the route the app uses.
 */
export async function clearDataStoreTable(
	api: FrappeApi,
	dataSource: string,
	tableName: string,
): Promise<void> {
	const name = await findTableDocName(api, dataSource, tableName)
	if (!name) return
	const docs = await api.getDoc(DOCTYPE.TABLE, name)
	await api.callMethod('insights.api.run_doc_method', {
		method: 'clear_warehouse_data',
		docs,
		args: {},
	})
}

/**
 * Remove an uploaded table and the file behind it.
 *
 * The Data Store copy goes first, because dropping it needs the table document
 * that the next call deletes. Files are matched on a prefix, so a stray left by
 * a killed run is cleared too.
 */
export async function deleteUploadedTable(api: FrappeApi, table: UploadedTable): Promise<void> {
	await clearDataStoreTable(api, table.dataSource, table.table).catch(() => {})
	const name = await findTableDocName(api, table.dataSource, table.table).catch(() => null)
	if (name) {
		await api.deleteDoc(DOCTYPE.TABLE, name).catch(() => {})
	}
	if (table.file) {
		await api.deleteDoc('File', table.file).catch(() => {})
	}
	await deleteUploadedFiles(api, table.table)
}

/** Delete every File whose name starts with `prefix`. */
export async function deleteUploadedFiles(api: FrappeApi, prefix: string): Promise<void> {
	const files = await api
		.getList<{ name: string }>('File', {
			fields: ['name'],
			filters: { file_name: ['like', `${prefix}%`] },
			limit: 0,
		})
		.catch(() => [])
	for (const file of files) {
		await api.deleteDoc('File', file.name).catch(() => {})
	}
}
