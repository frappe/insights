import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ChartBuilderActions from './ChartBuilderActions.vue'

// Duplicate uses the router, which needs a mounted page
vi.mock('../../workbook/workbook_items', () => ({ duplicateWorkbookItem: () => {} }))
vi.mock('../../session', () => ({ default: { user: { has_desk_access: true } } }))
vi.mock('frappe-ui', async (original) => ({
	...(await original<typeof import('frappe-ui')>()),
	Dropdown: {
		props: ['options'],
		render() {
			return h('span', (this as any).options.map((option: any) => option.label).join('|'))
		},
	},
}))

// For a caller who may not write the chart, the server returns the View's
// result, which has no SQL.

async function menu(
	executedSQL: string,
	doc: Record<string, any> = {},
	chart: Record<string, any> = {},
) {
	const app = createSSRApp({
		render: () =>
			h(ChartBuilderActions, {
				chart: reactive({ doc: { read_only: !executedSQL, ...doc }, ...chart }),
				preview: reactive({ result: { executedSQL } }) as any,
				chartEl: null,
				onDownload: () => {},
				onShare: () => {},
			}),
	})
	// The app registers frappe-ui components globally. This test does not, so it
	// silences the warnings for unresolved components.
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('the builder card menu', () => {
	// @feature charts.view-sql permissions.viewer-cannot-edit
	it('shows the SQL only where the server sent it', async () => {
		expect(await menu('select 1')).toContain('View SQL')
		expect(await menu('')).not.toContain('View SQL')
	})

	// @feature shared.publish-needs-share
	it('shows Share where the server says the caller may share, and nowhere else', async () => {
		expect(await menu('select 1', { can_share: true })).toContain('Share Chart')
		expect(await menu('select 1', { can_share: false })).not.toContain('Share Chart')
	})

	// @feature desk.show-in-desk
	it('offers Show in Desk for a saved chart where the server says the caller may create it', async () => {
		const may = { can_show_in_desk: true }
		expect(await menu('select 1', may, { islocal: false })).toContain('Show in Desk')
		expect(await menu('select 1', may, { islocal: true })).not.toContain('Show in Desk')
		expect(
			await menu('select 1', { can_show_in_desk: false }, { islocal: false }),
		).not.toContain('Show in Desk')
	})
})
