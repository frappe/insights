import { beforeEach, describe, expect, it, vi } from 'vitest'

const calls = vi.hoisted(() => [] as { method: string; args: any }[])
const answer = vi.hoisted(() => ({ dashboard: {} as any, refuseSave: false }))

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	// a refused save shows a toast, which needs a DOM
	toast: { error: () => {} },
	call: (method: string, args: any) => {
		calls.push({ method, args })
		if (method === 'insights.api.view.get_dashboard') {
			return answer.dashboard instanceof Error
				? Promise.reject(answer.dashboard)
				: Promise.resolve(answer.dashboard)
		}
		if (answer.refuseSave && method === 'frappe.client.set_value') {
			return Promise.reject(Object.assign(new Error('refused'), { status: 417 }))
		}
		if (
			(method === 'insights.api.get_doc' || method === 'frappe.client.set_value') &&
			args.doctype === 'Insights Dashboard v3'
		) {
			return Promise.resolve({
				doctype: 'Insights Dashboard v3',
				name: 'dashboard-1',
				owner: 'author@example.com',
				title: args.fieldname?.title ?? 'Sales',
				items: '[]',
			})
		}
		if (method === 'insights.api.get_doc' || method === 'frappe.client.set_value') {
			return Promise.resolve({
				doctype: 'Insights Chart v3',
				name: 'chart-1',
				owner: 'author@example.com',
				title: args.fieldname?.title ?? 'Revenue',
				chart_type: 'Bar',
				config: '{}',
			})
		}
		// a card's rows come with the chart they were computed from
		const chart = answer.dashboard.charts.find((chartDoc: any) => chartDoc.name === args.chart)
		return Promise.resolve({ chart, columns: [], rows: [] })
	},
}))

// the SPA's router needs a browser's history, and nothing here navigates
vi.mock('../router', () => ({ default: {} }))

// stays open until a test confirms it, like the real dialog
const confirming = vi.hoisted(() => ({ onSuccess: undefined as undefined | (() => any) }))
vi.mock('../helpers/confirm_dialog', () => ({
	confirmDialog: ({ onSuccess }: { onSuccess: () => any }) => (confirming.onSuccess = onSuccess),
}))

// the reader's filter choices persist here between visits
vi.stubGlobal('document', { cookie: '' })
const stored = vi.hoisted(() => new Map<string, string>())
vi.stubGlobal('localStorage', {
	getItem: (key: string) => stored.get(key) ?? null,
	setItem: (key: string, value: string) => stored.set(key, value),
	removeItem: (key: string) => stored.delete(key),
})

import useChart from '../charts/chart'
import useDashboard from './dashboard'
import { nextTick, ref } from 'vue'
import { cellRulesFor, useDashboardView, watchFilterDefault } from './view'

const layout = { i: '1', x: 0, y: 0, w: 20, h: 8 }

function dashboardAnswer(chart_type: string) {
	return {
		name: 'dashboard-1',
		route: 'sales',
		title: 'Sales',
		items: [
			{ type: 'chart', chart: 'chart-1', layout },
			{
				type: 'filter',
				filter_name: 'region',
				filter_type: 'String',
				charts: ['chart-1'],
				layout: { ...layout, i: '2' },
			},
		],
		charts: [{ name: 'chart-1', title: 'Revenue', chart_type, config: {} }],
		vertical_compact_layout: true,
		can_write: false,
		can_copy: false,
		workbook: null,
	}
}

const settled = () => new Promise((resolve) => setTimeout(resolve, 0))

/** Pages outlive their mounts, so each test uses its own route. */
async function opened(route = 'sales') {
	const view = useDashboardView(() => route, 'dashboards')
	await settled()
	return view
}

const dashboardCalls = () =>
	calls.filter((call) => call.method === 'insights.api.view.get_dashboard')

const dataCalls = () => calls.filter((call) => call.method === 'insights.api.view.get_chart_data')

beforeEach(() => {
	calls.length = 0
	stored.clear()
	answer.dashboard = dashboardAnswer('Bar')
	answer.refuseSave = false
})

// A reader leaves a dashboard and comes back. The SPA route rebuilds the page
// component, but card reads are cached per read context (`ChartReadContext`). A
// second page state for one read context would leave every card reading a state
// nobody sees.
describe('a dashboard opened a second time', () => {
	// @feature dashboard.filter-links
	it('runs the cards a filter reaches under the filter the reader moved', async () => {
		await opened()
		const second = await opened()
		const before = dataCalls().length

		second.setFilter('region', { operator: '=', value: 'north' })
		await settled()

		const ran = dataCalls().slice(before)
		expect(ran).toHaveLength(1)
		expect(ran[0].args.filters).toEqual({ region: { operator: '=', value: 'north' } })
	})

	// @feature dashboard.loads charts.one-snapshot
	it('renders the page the reader left and asks the server nothing', async () => {
		const first = await opened('left')
		const asked = calls.length

		answer.dashboard = dashboardAnswer('Line')
		const second = await opened('left')

		expect(calls).toHaveLength(asked)
		expect(second.chartView('chart-1')).toBe(first.chartView('chart-1'))
		expect(second.chartView('chart-1')?.doc.chart_type).toBe('Bar')
	})
})

// The server tells a missing dashboard from one the reader may not read, and
// says nothing else about the second.
describe('a dashboard the reader may not open', () => {
	const refused = (exc_type: string, messages: string[] = []) =>
		Object.assign(new Error(exc_type), { exc_type, messages })

	// @feature permissions.denied-says-no-access permissions.no-access-names-roles
	it('says Not Found for a reference that names nothing, and No Access for a refusal', async () => {
		answer.dashboard = refused('DoesNotExistError')
		const missing = await opened('missing')
		answer.dashboard = refused('PermissionError', ["You don't have access to this dashboard"])
		const denied = await opened('denied')
		answer.dashboard = refused('SharedWithRoles', ['Shared with Stock User'])
		const shared = await opened('shared')

		expect([missing.notFound, missing.noAccess, missing.failed]).toEqual([
			true,
			undefined,
			false,
		])
		expect([denied.notFound, denied.noAccess, denied.failed]).toEqual([
			false,
			{ doctypes: [], sharedWith: undefined },
			false,
		])
		expect(shared.noAccess).toEqual({ doctypes: [], sharedWith: 'Shared with Stock User' })
		expect(denied.title).toBe('')
		expect(dataCalls()).toHaveLength(0)
	})

	// @feature permissions.no-access-when-nothing-is-permitted
	it('names the doctypes its charts need when the reader may read none of their data', async () => {
		answer.dashboard = { not_permitted: { doctypes: ['Sales Invoice'] } }
		const view = await opened('refused-data')

		expect(view.noAccess).toEqual({ doctypes: ['Sales Invoice'] })
		expect([view.notFound, view.failed, view.items]).toEqual([false, false, []])
		expect(dataCalls()).toHaveLength(0)
	})
})

// A dashboard shipped by an app is read-only. To change it, a site duplicates
// its workbook.
describe('a shipped dashboard', () => {
	// @feature standard.duplicate
	it('shows Duplicate only to a reader the server lets copy it', async () => {
		answer.dashboard = { ...dashboardAnswer('Bar'), can_copy: true, workbook: 'workbook-1' }
		const copyable = await opened('shipped')
		expect(copyable.duplicate).toBeTypeOf('function')
		expect(copyable.builderRoute).toBeUndefined()
		expect(copyable.chartRoute?.('chart-1')).toBeUndefined()

		answer.dashboard = dashboardAnswer('Bar')
		const readOnly = await opened('shipped-for-a-desk-reader')
		expect(readOnly.duplicate).toBeUndefined()
	})

	// @feature standard.duplicate
	it('duplicates the workbook the server named', async () => {
		answer.dashboard = { ...dashboardAnswer('Bar'), can_copy: true, workbook: 'workbook-1' }
		const view = await opened('shipped-and-copied')

		view.duplicate!()
		await settled()

		expect(calls.find((call) => call.method === 'run_doc_method')?.args).toEqual({
			dt: 'Insights Workbook',
			dn: 'workbook-1',
			method: 'duplicate',
		})
	})
})

describe('a dashboard refreshed', () => {
	// @feature charts.refresh charts.one-snapshot
	it('reads the dashboard again, and runs every card past the cache with it', async () => {
		const view = await opened('refreshed')
		const before = calls.length

		answer.dashboard = dashboardAnswer('Line')
		view.refresh(true)
		await settled()

		const asked = calls.slice(before)
		expect(asked.map((call) => call.method)).toEqual([
			'insights.api.view.get_dashboard',
			'insights.api.view.get_chart_data',
		])
		expect(asked[1].args.force).toBe(true)
		expect(view.chartView('chart-1')?.doc.chart_type).toBe('Line')
		expect(dashboardCalls()).toHaveLength(2)
	})
})

describe('a filter with a default that the reader cleared', () => {
	// @feature dashboard.filter-clear dashboard.filter-default
	it('stays cleared when the dashboard is read again', async () => {
		const withDefault = dashboardAnswer('Bar')
		Object.assign(withDefault.items[1], { default_operator: '=', default_value: 'north' })
		answer.dashboard = withDefault
		const view = await opened('cleared')
		expect(view.filters).toEqual({ region: { operator: '=', value: 'north' } })

		view.setFilter('region')
		view.refresh()
		await settled()

		expect(view.filters).toEqual({})
	})
})

describe("an empty card's Reset filters", () => {
	// @feature charts.reset-filters dashboard.filter-default
	it("takes the filters back to the board's defaults, and stays hidden while they are there", async () => {
		const withDefault = dashboardAnswer('Bar')
		Object.assign(withDefault.items[1], { default_operator: '=', default_value: 'north' })
		answer.dashboard = withDefault
		const view = await opened('reset-to-default')
		expect(view.filtered('chart-1')).toBe(false)

		view.setFilter('region', { operator: '=', value: 'south' })
		expect(view.filtered('chart-1')).toBe(true)
		view.resetCardFilters('chart-1')
		expect(view.filters).toEqual({ region: { operator: '=', value: 'north' } })
		expect(view.filtered('chart-1')).toBe(false)

		// cleared by hand, the default is back after a reset and after a reload
		view.setFilter('region')
		expect(view.filtered('chart-1')).toBe(true)
		view.resetCardFilters('chart-1')
		view.refresh()
		await settled()
		expect(view.filters).toEqual({ region: { operator: '=', value: 'north' } })
	})
})

describe('a filter whose default arrives after the reader moved another filter', () => {
	// The default may be one the owner adds, or the reader's user default once
	// it is set. Both reach the View as the item's default.
	// @feature dashboard.filter-default
	it('opens with that default', async () => {
		const twoFilters = dashboardAnswer('Bar')
		const region = twoFilters.items[1]
		twoFilters.items.push({
			type: 'filter',
			filter_name: 'city',
			filter_type: 'String',
			charts: ['chart-1'],
			layout: { ...layout, i: '3' },
		})
		answer.dashboard = twoFilters
		const view = await opened('default-later')
		view.setFilter('city', { operator: '=', value: 'pune' })

		Object.assign(region, { default_operator: '=', default_value: 'north' })
		view.refresh()
		await settled()

		expect(view.filters).toEqual({
			region: { operator: '=', value: 'north' },
			city: { operator: '=', value: 'pune' },
		})
	})
})

describe('a chart its author saved in this tab', () => {
	// @feature charts.one-snapshot
	it('is asked again when a card that renders it mounts', async () => {
		const first = await opened('authored')
		const before = dataCalls().length

		const chart = useChart('chart-1')
		await settled()
		chart.doc.title = 'Revenue by month'
		await chart.save()

		// a cell loads its card's rows on mount, through `chart_cell.ts`
		const second = await opened('authored')
		second.loadChart('chart-1')
		await settled()

		expect(dataCalls().slice(before)).toHaveLength(1)
		expect(second.chartView('chart-1')).toBe(first.chartView('chart-1'))
	})
})

describe('a dashboard its author saved in this tab', () => {
	// @feature charts.one-snapshot
	it('is read again when its page mounts', async () => {
		await opened('arranged')
		const before = dashboardCalls().length

		const dashboard = useDashboard('dashboard-1')
		await settled()
		dashboard.doc.title = 'Sales by region'
		await dashboard.save()

		await opened('arranged')

		expect(dashboardCalls().slice(before)).toHaveLength(1)
	})

	// Relinking a filter to another column does not change a card's request,
	// because `present_item` hides filter links from the View.
	// @feature charts.one-snapshot
	it('runs every card again when its page mounts', async () => {
		await opened('relinked')
		const before = dataCalls().length

		const dashboard = useDashboard('dashboard-1')
		await settled()
		dashboard.doc.title = 'Sales by shipping region'
		await dashboard.save()

		await opened('relinked')

		expect(dataCalls().slice(before)).toHaveLength(1)
	})
})

// Refresh passes each mounted `DashboardFilter` a new `item`. The grid keys
// cells by layout, so the cell stays and only its props change.
describe('a filter cell whose item is replaced', () => {
	const filterItem = (default_value: string) => ({
		type: 'filter',
		filter_name: 'region',
		filter_type: 'String' as const,
		default_operator: '=' as const,
		default_value,
	})

	// @feature dashboard.filter-default
	it("keeps the reader's value while the default says the same", async () => {
		const item = ref(filterItem('north'))
		const applied: unknown[] = []
		watchFilterDefault(
			() => item.value,
			(operator, value) => applied.push([operator, value]),
		)

		item.value = filterItem('north')
		await nextTick()
		expect(applied).toEqual([])

		item.value = filterItem('south')
		await nextTick()
		expect(applied).toEqual([['=', 'south']])
	})
})

describe('an edit session the server refuses', () => {
	// @feature dashboard.move-resize
	it('stays in edit mode with every edit', async () => {
		const dashboard = useDashboard('dashboard-refused')
		await settled()
		dashboard.editing = true
		dashboard.doc.title = 'Sales by region'

		answer.refuseSave = true
		await expect(dashboard.finishEditing()).rejects.toThrow('refused')
		await settled()

		expect(dashboard.editing).toBe(true)
		expect(dashboard.doc.title).toBe('Sales by region')
	})
})

describe('an edit session the author discards', () => {
	const saves = () => calls.filter((call) => call.method === 'frappe.client.set_value')

	// @feature dashboard.move-resize
	it('saves nothing while the confirm is open, and leaves edit mode on the stored document', async () => {
		vi.useFakeTimers()
		try {
			const dashboard = useDashboard('dashboard-discarded')
			await vi.runAllTimersAsync()
			dashboard.editing = true
			dashboard.doc.title = 'Sales by region'

			dashboard.discardEditing()
			await vi.advanceTimersByTimeAsync(5000)
			expect(dashboard.editing).toBe(true)
			expect(saves()).toEqual([])

			await confirming.onSuccess!()
			await vi.advanceTimersByTimeAsync(5000)
			expect(dashboard.editing).toBe(false)
			expect(dashboard.doc.title).toBe('Sales')
			expect(saves()).toEqual([])
		} finally {
			vi.useRealTimers()
		}
	})
})

describe('Number cells in one row', () => {
	const number = (comparison: boolean) => ({
		chart_type: 'Number',
		config: {
			number_columns: [{ column_name: 'amount', measure_name: 'Amount', aggregation: 'sum' }],
			number_column_options: [comparison ? { comparison: { source: 'last year' } } : {}],
		},
	})
	const charts: Record<string, any> = {
		compared: number(true),
		plain: number(false),
		below: number(false),
	}
	const cell = (chart: string, x: number, y: number) =>
		({ type: 'chart', chart, layout: { i: chart, x, y, w: 7, h: 4 } }) as any

	// @feature dashboard.cell-height-rule
	it('take the height of the tallest, so the row ends level', () => {
		const rules = cellRulesFor(
			[cell('compared', 0, 3), cell('plain', 7, 3), cell('below', 0, 8)],
			(chart) => charts[chart],
		)

		expect(rules.compared.height).toBe(5)
		expect(rules.plain.height).toBe(5)
		// a row of its own keeps the height its reading needs
		expect(rules.below.height).toBe(4)
	})
})
