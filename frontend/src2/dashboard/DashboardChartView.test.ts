import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { makeChartRead } from '../charts/chart_view'
import DashboardChartView from './DashboardChartView.vue'
import type { DashboardView } from './view'

// What a table card offers its reader. The server refuses a reader's own filter
// on a chart run as its owner, so the card offers one only where it is answered.

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
		// find never leaves the browser, so it stays either way
		expect(await tableCard({ can_filter: false })).toContain('lucide-search')
	})
})
