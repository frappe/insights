import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import TableChart from './TableChart.vue'
import type { TableChartProps } from '../adapter/table'

// A Table is drawn outside a chart surface too: a drill level whose answer holds
// no numeric column falls back to a grid, and the dialog that draws it is
// `ChartBody`'s sibling, so nothing a surface provides is there.

const props: TableChartProps = {
	columns: [
		{ name: 'region', type: 'String' },
		{ name: 'order_date', type: 'Date' },
	],
	rows: [{ region: 'north', order_date: '2024-01-01' }],
	sortOrder: {},
}

describe('a grid drawn outside a chart surface', () => {
	// @feature charts.table-renders-outside-dashboard
	it('draws its rows instead of throwing', async () => {
		const app = createSSRApp({ render: () => h(TableChart, props) })
		// the app registers frappe-ui's components globally; this render is one
		// component and does not need them resolved
		app.config.warnHandler = () => {}
		expect(await renderToString(app)).toContain('north')
	})
})
