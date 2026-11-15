import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import type { ChartRead, ChartReadContext } from './chart_view'

let read: ChartRead
let context: ChartReadContext | undefined

vi.mock('./chart_view', async (importOriginal) => ({
	...(await importOriginal<object>()),
	useChartView: (_: string, readContext?: ChartReadContext) => {
		context = readContext
		return read
	},
}))

import { makeChartRead } from './chart_view'
import SharedChart from './SharedChart.vue'

async function sharedTable(can_filter: boolean) {
	read = makeChartRead({
		doc: { name: 'chart-1', title: 'Orders', chart_type: 'Table', config: {} as any },
		fetchData: () =>
			Promise.resolve({
				columns: [{ name: 'status', type: 'String' }],
				rows: [],
				can_filter,
			}),
		fetchDrillData: () => Promise.reject(new Error('not asked')),
	})
	await read.load()

	const app = createSSRApp({ render: () => h(SharedChart, { chart_name: 'chart-1' }) })
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('a table chart opened by its public link', () => {
	// @feature shared.chart-link dashboard.card-filter shared.no-drill
	it('gives the reader find, and a filter of their own only where the server allows one', async () => {
		const guest = await sharedTable(false)
		expect(guest).toContain('lucide-search')
		expect(guest).not.toContain('lucide-list-filter')

		expect(await sharedTable(true)).toContain('lucide-list-filter')
		expect(context?.filterContext('chart-1')).toEqual({ chart: 'chart-1', cardFilters: [] })
	})
})
