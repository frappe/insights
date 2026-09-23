import { describe, expect, it } from 'vitest'
import { createSSRApp, h, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { chartPreviewKey } from '../chart_preview'
import ChartBuilderTable from './ChartBuilderTable.vue'

// The rows under the builder's card are the chart's own table: its header sort
// and its date grain write the chart's config. `ChartBuilder.vue` makes the
// sidebar inert for a caller who may not write the chart, and this table sits
// outside it.

async function table(readOnly: boolean) {
	const columns = [
		{ name: 'order_date', type: 'Date' },
		{ name: 'count', type: 'Integer' },
	]
	const rows = [{ order_date: '2024-01-01', count: 3 }]
	const preview = reactive({
		ready: true,
		executing: false,
		result: {
			columns,
			rows,
			formattedRows: rows,
			totalRowCount: 1,
			executedSQL: 'select 1',
			timeTaken: 0.1,
		},
		currentOperations: [],
	})
	const app = createSSRApp({ render: () => h(ChartBuilderTable, { readOnly }) })
	app.provide('chart', reactive({ doc: { chart_type: 'Bar', config: {} } }))
	app.provide(chartPreviewKey, preview as any)
	// every menu a header draws — the sort, and the grain of a date column
	app.component('Dropdown', { render: () => h('span', { 'data-menu': '' }) })
	// the app registers frappe-ui's other components globally; this render does
	// not need them resolved
	app.config.warnHandler = () => {}
	return renderToString(app)
}

const menus = (html: string) => html.split('data-menu').length - 1

describe('the rows under the builder card', () => {
	// @feature charts.preview-table-sort charts.preview-table-grain permissions.chart-run-as-owner
	it('offers its sort and its date grain only to a caller who may write the chart', async () => {
		// a sort on each of the two columns, and the grain of the date one
		expect(menus(await table(false))).toBe(3)
		expect(menus(await table(true))).toBe(0)
	})
})
