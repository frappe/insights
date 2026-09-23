import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ChartBuilderActions from './ChartBuilderActions.vue'

// duplicating reaches the router, which reads the page it was mounted on
vi.mock('../../workbook/workbook_items', () => ({ duplicateWorkbookItem: () => {} }))
// the menu, drawn as the labels it offers
vi.mock('frappe-ui', async (original) => ({
	...(await original<typeof import('frappe-ui')>()),
	Dropdown: {
		props: ['options'],
		render() {
			return h('span', (this as any).options.map((option: any) => option.label).join('|'))
		},
	},
}))

// The builder card's menu. A caller who may not write the chart is answered
// with the view's picture, which carries no SQL.

async function menu(executedSQL: string, doc: Record<string, any> = {}) {
	const app = createSSRApp({
		render: () =>
			h(ChartBuilderActions, {
				chart: reactive({ doc: { read_only: !executedSQL, ...doc } }),
				preview: reactive({ result: { executedSQL } }) as any,
				chartEl: null,
				onDownload: () => {},
				onShare: () => {},
			}),
	})
	// the app registers frappe-ui's components globally; this render does not
	// need them resolved
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('the builder card menu', () => {
	// @feature charts.view-sql permissions.viewer-cannot-edit
	it('offers the SQL only where the server sent it', async () => {
		expect(await menu('select 1')).toContain('View SQL')
		expect(await menu('')).not.toContain('View SQL')
	})

	// @feature shared.publish-needs-share
	it('offers Share where the server says the caller may share, and nowhere else', async () => {
		expect(await menu('select 1', { can_share: true })).toContain('Share Chart')
		// a writer the server does not let share
		expect(await menu('select 1', { can_share: false })).not.toContain('Share Chart')
	})
})
