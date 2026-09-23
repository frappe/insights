import { beforeEach, describe, expect, it, vi } from 'vitest'

const calls = vi.hoisted(() => [] as { method: string; args: any }[])
const answer = vi.hoisted(() => ({ dashboard: {} as any, refuseSave: false }))

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	// a refusal is toasted, and the toast needs a DOM
	toast: { error: () => {} },
	call: (method: string, args: any) => {
		calls.push({ method, args })
		if (method === 'insights.api.view.get_dashboard') {
			return Promise.resolve(answer.dashboard)
		}
		if (answer.refuseSave && method === 'frappe.client.set_value') {
			return Promise.reject(Object.assign(new Error('refused'), { status: 417 }))
		}
		// the workbook's dashboard store, which an author edits and saves
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
		// the workbook's chart store, which an author edits and saves
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
		const chart = answer.dashboard.charts.find((frame: any) => frame.name === args.chart)
		return Promise.resolve({ chart, columns: [], rows: [] })
	},
}))

// the SPA's router needs a browser's history, and nothing here navigates
vi.mock('../router', () => ({ default: {} }))

// held open until a case answers it, as the dialog on screen is
const confirming = vi.hoisted(() => ({ onSuccess: undefined as undefined | (() => any) }))
vi.mock('../helpers/confirm_dialog', () => ({
	confirmDialog: ({ onSuccess }: { onSuccess: () => any }) => (confirming.onSuccess = onSuccess),
}))

// the browser's own, which a reader's filter choices live in between visits
vi.stubGlobal('document', { cookie: '' })
vi.stubGlobal('localStorage', {
	getItem: () => null,
	setItem: () => {},
	removeItem: () => {},
})

import useChart from '../charts/chart'
import useDashboard from './dashboard'
import { nextTick, ref } from 'vue'
import { useDashboardView, watchFilterDefault } from './view'

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

/** Everything the fetch and the cards it opens have to land before a case reads. */
const settled = () => new Promise((resolve) => setTimeout(resolve, 0))

/**
 * A reader opening `/dashboards/<route>`, as a mount of `Dashboard.vue` does.
 * Pages outlive their mounts, so each case names a dashboard of its own.
 */
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
	answer.dashboard = dashboardAnswer('Bar')
	answer.refuseSave = false
})

// A reader leaves a dashboard and comes back to it: the SPA's route rebuilds the
// page component, and the reads its cards draw from are cached under the
// surface. A second page state under one surface leaves every card reading the
// state nobody is looking at.
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
	it('draws the page the reader left and asks the server nothing', async () => {
		const first = await opened('left')
		const asked = calls.length

		answer.dashboard = dashboardAnswer('Line')
		const second = await opened('left')

		expect(calls).toHaveLength(asked)
		expect(second.chartView('chart-1')).toBe(first.chartView('chart-1'))
		expect(second.chartView('chart-1')?.doc.chart_type).toBe('Bar')
	})
})

// The header's Refresh, through `DashboardBody`'s `refresh`, which calls
// `refresh(true)` on the page it draws.
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

// An author edits a chart in the workbook, then opens a dashboard that draws it,
// in the same tab.
describe('a chart its author saved in this tab', () => {
	// @feature charts.one-snapshot
	it('is asked again when a card that draws it mounts', async () => {
		const first = await opened('authored')
		const before = dataCalls().length

		const chart = useChart('chart-1')
		await settled()
		chart.doc.title = 'Revenue by month'
		await chart.save()

		// a cell asks for its card's rows as it mounts, through `chart_cell.ts`
		const second = await opened('authored')
		second.loadChart('chart-1')
		await settled()

		expect(dataCalls().slice(before)).toHaveLength(1)
		expect(second.chartView('chart-1')).toBe(first.chartView('chart-1'))
	})
})

// An author arranges a dashboard in the workbook, then opens it, in the same tab.
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

	// A filter re-pointed to another column leaves a card's request byte-identical:
	// `present_item` withholds a filter's links from the view.
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

// Refresh hands every mounted `DashboardFilter` a new `item`: the grid keys its
// cells by layout, so the cell survives and its props are replaced.
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

// The builder's Done, which saves the edit session by hand.
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

// The builder's Reset Layout, which offers to throw the edit session away.
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
