import { describe, expect, it } from 'vitest'
import { createSSRApp, h, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { chartPreviewKey } from '../chart_preview'
import ChartBuilderTable from './ChartBuilderTable.vue'

// The table's header sort and date grain write the chart config.
// `ChartBuilder.vue` makes the sidebar inert for a caller who may not write the
// chart. This table is outside the sidebar, so it must hide them itself.

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
	app.component('Dropdown', { render: () => h('span', { 'data-menu': '' }) })
	// The app registers the other frappe-ui components globally. This test does
	// not, so it silences the warnings for unresolved components.
	app.config.warnHandler = () => {}
	return renderToString(app)
}

const menus = (html: string) => html.split('data-menu').length - 1

describe('the rows under the builder card', () => {
	// @feature charts.preview-table-sort charts.preview-table-grain permissions.chart-run-as-owner
	it('allows sort and date grain changes only to a caller who may write the chart', async () => {
		// a sort menu on each column, and a grain menu on the date column
		expect(menus(await table(false))).toBe(3)
		expect(menus(await table(true))).toBe(0)
	})
})
