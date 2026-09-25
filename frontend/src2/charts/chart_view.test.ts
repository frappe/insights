import { beforeEach, describe, expect, it, vi } from 'vitest'
import { reactive } from 'vue'
import useChartPreview from './chart_preview'
import type { Chart } from './chart'
import { makeChartRead, useChartView, type CardFilter } from './chart_view'
import type { DrillLevel } from './drill/drill_stack'

const calls = vi.hoisted(() => [] as any[])
const answers = vi.hoisted(() => new Map<string, (args: any) => Promise<any>>())

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: (method: string, args: any) => {
		calls.push({ method, args })
		const answer = answers.get(method)
		if (answer) return answer(args)
		return Promise.resolve({ message: { columns: [], rows: [] } })
	},
}))

beforeEach(() => {
	calls.length = 0
	answers.clear()
})

// A Number chart renders one cell per reading, and each cell loads the chart.
// On a public link the request had no key. So repeats were not dropped, and one
// chart ran its query once per reading.

describe('the request a public read would send', () => {
	// @feature shared.read-once
	it('is asked once, however many cards load the same chart under the same filters', async () => {
		const chartDoc = { name: 'chart-9', title: '', chart_type: 'Number', config: {} as any }
		const read = useChartView(chartDoc.name, undefined, chartDoc)

		await read.load()
		await read.load()

		expect(calls).toHaveLength(1)
	})

	// @feature shared.read-once
	it('is asked again when the surface narrows the chart differently', async () => {
		const cardFilters: CardFilter[] = []
		const chartDoc = { name: 'chart-10', title: '', chart_type: 'Number', config: {} as any }
		const read = useChartView(
			chartDoc.name,
			{
				id: 'dashboard:dashboard-9',
				filterContext: (chart_name) => ({
					chart: chart_name,
					dashboard: 'dashboard-9',
					cardFilters: [...cardFilters],
				}),
			},
			chartDoc,
		)

		await read.load()
		expect(calls).toHaveLength(1)

		cardFilters.push({ column: 'city', operator: '=', value: 'delhi' })
		await read.load()
		expect(calls).toHaveLength(2)
	})
})

// A card drops a load that repeats its last request. A Refresh is not a repeat.
// A failed run shows no rows, so the next load runs again and clears the error.

function readAnswering(answer: (attempt: number) => Promise<any>) {
	const forces: boolean[] = []
	let attempts = 0
	const read = makeChartRead({
		doc: { name: 'chart-2', title: 'Sales', chart_type: 'Table', config: {} as any },
		requestKey: () => 'the same question',
		fetchData: (force) => {
			forces.push(force)
			return answer(++attempts)
		},
		fetchDrillData: () => Promise.reject(new Error('not asked')),
	})
	return { read, forces }
}

const northThenSouth = (attempt: number) =>
	Promise.resolve({
		columns: [{ name: 'region', type: 'String' }],
		rows: [{ region: attempt === 1 ? 'North' : 'South' }],
	})

describe('a card asked for its rows again', () => {
	// @feature charts.refresh
	it('a refresh asks the server again, past the cache', async () => {
		const { read, forces } = readAnswering(northThenSouth)

		await read.load()
		expect(read.result.rows).toEqual([{ region: 'North' }])

		await read.load()
		expect(forces).toEqual([false])
		expect(read.result.rows).toEqual([{ region: 'North' }])

		await read.load(true)
		expect(forces).toEqual([false, true])
		expect(read.result.rows).toEqual([{ region: 'South' }])
	})

	// @feature charts.retry
	it('a retry after a failed run asks again and clears the error', async () => {
		const { read } = readAnswering((attempt) =>
			attempt === 1
				? Promise.reject(new Error('Table orders is gone'))
				: northThenSouth(attempt),
		)

		await read.load()
		expect(read.failed).toBe(true)
		expect(read.failure).toBe('Table orders is gone')
		expect(read.result.rows).toEqual([])

		await read.load()
		expect(read.failed).toBe(false)
		expect(read.failure).toBe('')
		expect(read.result.rows).toEqual([{ region: 'South' }])
	})
})

describe('a link to a chart the reader cannot open', () => {
	// @feature shared.missing-link
	it('fails with the server sentence instead of loading forever', async () => {
		answers.set('insights.api.view.get_chart', () => Promise.reject(new Error('Not Found')))
		const read = useChartView('chart-missing')

		await read.load()

		expect(read.executing).toBe(false)
		expect(read.failed).toBe(true)
		expect(read.failure).toBe('Not Found')
	})
})

// Not Permitted is a result, not a failure. The reader cannot retry or fix it,
// so the card must not show either.

describe('a card the reader may not read the data behind', () => {
	// @feature permissions.not-permitted-chart
	it('names the doctypes it needs and reports no failure and no rows', async () => {
		const { read } = readAnswering((attempt) =>
			attempt === 1
				? Promise.resolve({ not_permitted: { doctypes: ['Sales Invoice'] } })
				: northThenSouth(attempt),
		)

		await read.load()
		expect(read.notPermitted).toEqual(['Sales Invoice'])
		expect(read.failed).toBe(false)
		expect(read.result.rows).toEqual([])

		await read.load(true)
		expect(read.notPermitted).toBeUndefined()
		expect(read.result.rows).toEqual([{ region: 'South' }])
	})
})

describe('a card the reader sees a narrowed set of rows on', () => {
	// @feature permissions.card-says-it-is-scoped
	it('holds what narrowed them, and drops it when the next answer names none', async () => {
		const { read } = readAnswering((attempt) =>
			attempt === 1
				? Promise.resolve({
						columns: [{ name: 'region', type: 'String' }],
						rows: [{ region: 'North' }],
						user_permissions: [{ doctype: 'Territory', documents: ['North'] }],
				  })
				: northThenSouth(attempt),
		)

		await read.load()
		expect(read.scopedBy).toEqual([{ doctype: 'Territory', documents: ['North'] }])

		await read.load(true)
		expect(read.scopedBy).toBeUndefined()
	})

	// @feature permissions.card-says-it-is-scoped
	it('holds a narrowing that names nothing, and drops it the same way', async () => {
		const { read } = readAnswering((attempt) =>
			attempt === 1
				? Promise.resolve({
						columns: [{ name: 'region', type: 'String' }],
						rows: [{ region: 'North' }],
						narrowed_by_permissions: true,
				  })
				: northThenSouth(attempt),
		)

		await read.load()
		expect(read.narrowedByPermissions).toBe(true)

		await read.load(true)
		expect(read.narrowedByPermissions).toBe(false)
	})
})

// A card takes the chart definition and its rows from one response. A newer
// definition must not render over older rows. A renamed measure would show no
// series, and a changed chart type would read columns that are not there.

function deferred<T>() {
	let resolve!: (value: T) => void
	const promise = new Promise<T>((settle) => (resolve = settle))
	return { promise, resolve }
}

const settled = () => new Promise((resolve) => setTimeout(resolve, 0))

function chartDocOf(name: string, title: string) {
	return { name, title, chart_type: 'Table', config: {} as any }
}

function rowsOf(chartDoc: ReturnType<typeof chartDocOf>, region: string) {
	return { chart: chartDoc, columns: [{ name: 'region', type: 'String' }], rows: [{ region }] }
}

describe('a card and the chart it renders', () => {
	// @feature charts.one-snapshot
	it('keeps the chart document it rendered its rows with when a revisit hands it a newer one', async () => {
		// `view.ts` `openReads` passes each read the chart document from the dashboard
		// response, on every visit. The rows on screen belong to the first chart document.
		const first = chartDocOf('chart-20', 'Sales')
		answers.set('insights.api.view.get_chart_data', () =>
			Promise.resolve(rowsOf(first, 'North')),
		)
		await useChartView(first.name, undefined, first).load()

		const read = useChartView(first.name, undefined, chartDocOf(first.name, 'Sales by region'))

		expect(read.doc.title).toBe('Sales')
		expect(read.result.rows).toEqual([{ region: 'North' }])
	})

	// @feature charts.one-snapshot charts.refresh
	it('renders a refreshed chart only once its new rows have landed', async () => {
		// `SharedChart` and `ChartIsland` open a chart without a chart document. The card's
		// Refresh reloads it with force.
		answers.set('insights.api.view.get_chart', () =>
			Promise.resolve(chartDocOf('chart-21', 'Sales')),
		)
		answers.set('insights.api.view.get_chart_data', () =>
			Promise.resolve(rowsOf(chartDocOf('chart-21', 'Sales'), 'North')),
		)
		const read = useChartView('chart-21')
		await read.load()
		expect(read.doc.title).toBe('Sales')

		const edited = chartDocOf('chart-21', 'Sales by region')
		const rows = deferred<any>()
		answers.set('insights.api.view.get_chart', () => Promise.resolve(edited))
		answers.set('insights.api.view.get_chart_data', () => rows.promise)
		const refreshed = read.load(true)
		await settled()

		expect(read.doc.title).toBe('Sales')
		expect(read.result.rows).toEqual([{ region: 'North' }])

		rows.resolve(rowsOf(edited, 'South'))
		await refreshed
		expect(read.doc.title).toBe('Sales by region')
		expect(read.result.rows).toEqual([{ region: 'South' }])
	})

	// @feature charts.drill-changed-chart
	it('drills the version of the chart it rendered, not the one a revisit handed it', async () => {
		// `ChartDrillDown.vue` sends the subject's `modified` with each level.
		// `view.get_drill_data` refuses a stale `modified`.
		const first = { ...chartDocOf('chart-23', 'Sales'), modified: '2026-09-22 10:00:00' }
		answers.set('insights.api.view.get_chart_data', () =>
			Promise.resolve(rowsOf(first, 'North')),
		)
		await useChartView(first.name, undefined, first).load()

		const read = useChartView(first.name, undefined, {
			...first,
			modified: '2026-09-22 11:00:00',
		})

		expect(read.drillSubject.modified).toBe('2026-09-22 10:00:00')
	})

	// @feature charts.one-snapshot shared.read-once
	it('is not asked again when the island that renders it is mounted again', async () => {
		// Desk's `chart_widget.js` remounts `ChartIsland` on every render. Each
		// mount opens the chart by name and loads it.
		answers.set('insights.api.view.get_chart', () =>
			Promise.resolve(chartDocOf('chart-22', 'Sales')),
		)
		answers.set('insights.api.view.get_chart_data', () =>
			Promise.resolve(rowsOf(chartDocOf('chart-22', 'Sales'), 'North')),
		)
		await useChartView('chart-22').load()
		const asked = calls.length

		const again = useChartView('chart-22')
		await again.load()

		expect(calls).toHaveLength(asked)
		expect(again.doc.title).toBe('Sales')
		expect(again.result.rows).toEqual([{ region: 'North' }])
	})
})

describe('the builder grid rendering a chart its author edited', () => {
	// @feature charts.one-snapshot charts.preview
	it('renders the config its rows answer until the edited config has its own rows', async () => {
		// `dashboard.ts` `chartView` gives the grid the workbook's chart store,
		// which the chart builder edits in place. `builder.ts` `loadChart` loads
		// each card when the grid mounts.
		const chart = reactive({
			doc: {
				name: 'chart-30',
				title: 'Sales',
				chart_type: 'Table',
				query: 'query-30',
				config: { limit: 10 } as any,
			},
		}) as unknown as Chart
		const context = {
			id: 'dashboard:dashboard-30',
			filterContext: (chart_name: string) => ({ chart: chart_name, cardFilters: [] }),
		}
		answers.set('insights.api.authoring.get_chart_data', () =>
			Promise.resolve({
				columns: [{ name: 'region', type: 'String' }],
				rows: [{ region: 'North' }],
			}),
		)
		const read = useChartPreview(chart, context)
		await read.load()

		chart.doc.config = { limit: 1 } as any
		expect(read.doc.config.limit).toBe(10)

		const rows = deferred<any>()
		answers.set('insights.api.authoring.get_chart_data', () => rows.promise)
		const edited = read.load()
		await settled()
		expect(read.doc.config.limit).toBe(10)
		expect(read.result.rows).toEqual([{ region: 'North' }])

		rows.resolve({ columns: [{ name: 'region', type: 'String' }], rows: [{ region: 'South' }] })
		await edited
		expect(read.doc.config.limit).toBe(1)
		expect(read.result.rows).toEqual([{ region: 'South' }])
	})
})

describe('the builder drilling a chart its author is editing', () => {
	// @feature charts.drill-changed-chart charts.preview
	it('drills the version its rows ran as, not the one the document being edited holds', async () => {
		// `ChartDrillDown.vue` sends the subject's `modified` with each level.
		// `authoring.get_drill_data` refuses it after a teammate saves the chart.
		const chart = reactive({
			doc: {
				name: 'chart-34',
				title: 'Sales',
				chart_type: 'Table',
				query: 'query-34',
				modified: '2026-09-22 09:00:00',
				config: { limit: 10 } as any,
			},
		}) as unknown as Chart
		answers.set('insights.api.authoring.get_chart_data', () =>
			Promise.resolve({
				modified: '2026-09-22 10:00:00',
				columns: [{ name: 'region', type: 'String' }],
				rows: [{ region: 'North' }],
			}),
		)
		const read = useChartPreview(chart)
		await read.load()

		expect(read.drillSubject.modified).toBe('2026-09-22 10:00:00')
	})

	// @feature charts.drill-segment charts.one-snapshot charts.preview
	it('drills the config on screen while an edit waits for its rows', async () => {
		// `ChartDrillDown.vue` reads the clicked segment from `subject.chart`.
		// `ChartBuilder.vue` loads an edit only after a debounce.
		const chart = reactive({
			doc: {
				name: 'chart-35',
				title: 'Sales',
				chart_type: 'Table',
				query: 'query-35',
				config: { limit: 10 } as any,
			},
		}) as unknown as Chart
		answers.set('insights.api.authoring.get_chart_data', () =>
			Promise.resolve({ columns: [{ name: 'region', type: 'String' }], rows: [] }),
		)
		const read = useChartPreview(chart)
		await read.load()

		chart.doc.config = { limit: 1 } as any
		const level: DrillLevel = { segment_filters: [], action: { rows: true } }
		await read.drillSubject.fetch([level])
		await read.drillSubject.rows!([level]).read({
			row_filters: [],
			sort: [],
			find: '',
			page: 1,
		})

		const drilled = calls.filter((c) => c.method === 'insights.api.authoring.get_drill_data')
		expect((read.drillSubject.chart.config as any).limit).toBe(10)
		expect(drilled.map((c) => c.args.config.limit)).toEqual([10, 10])
	})
})

describe('the builder rendering a chart its reader may not write', () => {
	// @feature charts.one-snapshot charts.preview
	it('renders the chart the server ran when that is not the one it sent', async () => {
		// For a collaborator who may not write the chart,
		// `authoring.get_chart_data` runs the stored chart and returns it.
		const chart = reactive({
			doc: {
				name: 'chart-31',
				title: 'Sales, edited',
				chart_type: 'Table',
				query: 'query-31',
				config: { limit: 1 } as any,
			},
		}) as unknown as Chart
		answers.set('insights.api.authoring.get_chart_data', () =>
			Promise.resolve({
				chart: {
					name: 'chart-31',
					title: 'Sales',
					chart_type: 'Table',
					config: { limit: 10 },
				},
				columns: [{ name: 'region', type: 'String' }],
				rows: [{ region: 'North' }],
			}),
		)
		const read = useChartPreview(chart)
		await read.load()

		expect(read.doc.title).toBe('Sales')
		expect(read.doc.config.limit).toBe(10)
	})

	// @feature charts.one-snapshot charts.preview
	it('fills the slots of the chart the server ran, as a saved card does', async () => {
		// A View's chart document holds only what the owner set, and never `filters`.
		const chart = reactive({
			doc: {
				name: 'chart-33',
				title: 'Sales',
				chart_type: 'Table',
				query: 'query-33',
				config: { limit: 1 } as any,
			},
		}) as unknown as Chart
		answers.set('insights.api.authoring.get_chart_data', () =>
			Promise.resolve({
				chart: { name: 'chart-33', title: 'Sales', chart_type: 'Table', config: {} },
				columns: [{ name: 'region', type: 'String' }],
				rows: [{ region: 'North' }],
			}),
		)
		const read = useChartPreview(chart)
		await read.load()

		expect(read.doc.config.limit).toBe(100)
		expect(read.doc.config.order_by).toEqual([])
		expect(read.doc.config.filters).toEqual({ filters: [], logical_operator: 'And' })
	})

	// @feature charts.preview permissions.chart-run-as-owner
	it('says its reader may not write it', () => {
		const chart = reactive({
			doc: {
				name: 'chart-32',
				title: 'Sales',
				chart_type: 'Table',
				query: 'q',
				config: {} as any,
				read_only: true,
			},
		}) as unknown as Chart

		expect(useChartPreview(chart).doc.can_write).toBe(false)
	})
})

// A Table chart pages only when the server says the reader may read its rows
// (`can_read_rows`). Other readers get the chart's first page only.

function pagedRead(chart_type: string, answer: (page: number) => Promise<any>) {
	const pages: number[] = []
	let question = 'todos by status'
	const read = makeChartRead({
		doc: { name: 'chart-3', title: 'Todos', chart_type, config: {} as any },
		requestKey: () => question,
		fetchData: (_force, _filterContext, page) => {
			pages.push(page)
			return answer(page)
		},
		fetchCount: () => Promise.resolve(250),
		fetchExport: () => Promise.resolve('region\nNorth'),
		fetchDrillData: () => Promise.reject(new Error('not asked')),
	})
	return { read, pages, ask: (next: string) => (question = next) }
}

const allowed = (page: number) =>
	northThenSouth(page).then((answer) => ({ ...answer, can_read_rows: true, can_export: true }))

describe('a card paged past its first page', () => {
	// @feature charts.table-pager
	it('asks for the next page of the same question, and a new question starts on the first', async () => {
		const { read, pages, ask } = pagedRead('Table', allowed)

		await read.load()
		await read.goToPage!(2)
		await read.load()
		expect(read.currentPage).toBe(2)

		ask('todos by owner')
		await read.load()

		expect(pages).toEqual([1, 2, 1])
		expect(read.currentPage).toBe(1)
	})

	// @feature charts.table-pager
	it('keeps a chart that is not a table on one page', async () => {
		const { read, pages } = pagedRead('Bar', allowed)

		await read.load()

		expect(pages).toEqual([1])
		expect(read.pageSize).toBeUndefined()
		expect(read.goToPage).toBeUndefined()
		expect(read.fetchResultCount).toBeUndefined()
	})

	// @feature charts.table-pager charts.export-rows permissions.chart-run-as-owner
	it('shows a reader allowed only the chart no page, no count and no file', async () => {
		const { read } = pagedRead('Table', (page) =>
			northThenSouth(page).then((answer) => ({
				...answer,
				can_read_rows: false,
				can_export: false,
			})),
		)

		await read.load()

		expect(read.goToPage).toBeUndefined()
		expect(read.fetchResultCount).toBeUndefined()
		expect(read.exportResults).toBeUndefined()
	})

	// @feature charts.export-rows
	it('allows export only where the server says the reader may export', async () => {
		const { read } = pagedRead('Table', (page) =>
			northThenSouth(page).then((answer) => ({ ...answer, can_read_rows: true })),
		)

		await read.load()

		expect(read.goToPage).toBeDefined()
		expect(read.exportResults).toBeUndefined()
	})
})
