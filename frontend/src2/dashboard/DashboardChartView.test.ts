import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { makeChartRead } from '../charts/chart_view'
import DashboardChartView from './DashboardChartView.vue'
import type { DashboardView } from './view'

// The server refuses a reader's card filter on a chart that runs as its owner.
// So the card shows the filter only when the server allows it.

async function tableCard(answer: Record<string, unknown>) {
	const read = makeChartRead({
		doc: { name: 'chart-1', title: 'Orders', chart_type: 'Table', config: {} as any },
		fetchData: () =>
			Promise.resolve({ columns: [{ name: 'status', type: 'String' }], rows: [], ...answer }),
		fetchDrillData: () => Promise.reject(new Error('not asked')),
	})
	await read.load()

	const dashboard = {
		chartView: () => read,
		loadChart: () => {},
		cardFilters: {},
		filtered: () => false,
	} as unknown as DashboardView
	const app = createSSRApp({
		render: () => h(DashboardChartView, { item: { chart: 'chart-1' } as any, dashboard }),
	})
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('a table card a reader is given', () => {
	// @feature dashboard.card-filter permissions.chart-run-as-owner
	it('offers a filter of their own only where `view.get_chart_data` says they may', async () => {
		expect(await tableCard({ can_filter: true })).toContain('lucide-list-filter')
		expect(await tableCard({ can_filter: false })).not.toContain('lucide-list-filter')
		// find runs in the browser, so it stays either way
		expect(await tableCard({ can_filter: false })).toContain('lucide-search')
	})
})
