import { describe, expect, it } from 'vitest'
import { createSSRApp, defineComponent, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { makeChartRead } from '../charts/chart_view'
import { useChartCell } from './chart_cell'
import DashboardChartView from './DashboardChartView.vue'
import type { DashboardView } from './view'

// The server refuses a reader's card filter on a chart that runs as its owner.
// So the card shows the filter only when the server allows it.

async function render(
	component: any,
	chart_type: string,
	answer: Record<string, unknown>,
	config = {},
) {
	const read = makeChartRead({
		doc: {
			name: 'chart-1',
			title: 'Orders',
			chart_type: chart_type as any,
			config: config as any,
		},
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
		render: () => h(component, { item: { chart: 'chart-1' } as any, dashboard }),
	})
	app.config.warnHandler = () => {}
	return renderToString(app)
}

const tableCard = (answer: Record<string, unknown>) => render(DashboardChartView, 'Table', answer)

// the columns the card's filter offers, one per line
const FilterColumns = defineComponent({
	props: ['item', 'dashboard'],
	setup(props) {
		const { columns } = useChartCell(props as any)
		return () => h('pre', columns.value.map((column) => column.name).join('\n'))
	},
})

describe('a table card a reader is given', () => {
	// @feature dashboard.card-filter permissions.chart-run-as-owner
	it('allows a filter of their own only where `view.get_chart_data` says they may', async () => {
		expect(await tableCard({ can_filter: true })).toContain('lucide-list-filter')
		expect(await tableCard({ can_filter: false })).not.toContain('lucide-list-filter')
		// find runs in the browser, so it stays either way
		expect(await tableCard({ can_filter: false })).toContain('lucide-search')
	})
})

describe('a chart card a reader is given', () => {
	// @feature dashboard.card-filter
	it('has a filter but no find, and a number card has neither', async () => {
		const bar = await render(DashboardChartView, 'Bar', {})
		expect(bar).toContain('lucide-list-filter')
		expect(bar).not.toContain('lucide-search')

		const number = await render(DashboardChartView, 'Number', {})
		expect(number).not.toContain('lucide-list-filter')
		expect(number).not.toContain('lucide-search')
	})

	// @feature dashboard.card-filter
	it("offers a split chart's x-axis and not the series the split made", async () => {
		const columns = [
			{ name: 'city', type: 'String' },
			{ name: 'Open', type: 'Integer' },
			{ name: 'Closed', type: 'Integer' },
		]
		const x_axis = { dimension: { column_name: 'city', dimension_name: 'city' } }
		const split_by = { dimension: { column_name: 'status', dimension_name: 'status' } }

		const split = await render(FilterColumns, 'Bar', { columns }, { x_axis, split_by })
		expect(split).toBe('<pre>city</pre>')

		const plain = await render(FilterColumns, 'Bar', { columns }, { x_axis })
		expect(plain).toBe('<pre>city\nOpen\nClosed</pre>')
	})
})
