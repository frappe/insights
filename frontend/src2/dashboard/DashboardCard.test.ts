import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import DashboardCard from './DashboardCard.vue'
import type { DashboardListItem } from './dashboards'

const NO_SHARED_PREVIEW = "Each viewer sees their own data, so there's no shared preview"

async function card(dashboard: Partial<DashboardListItem>) {
	const app = createSSRApp({
		render: () =>
			h(DashboardCard, {
				dashboard: {
					name: 'sales',
					title: 'Sales',
					owner_name: 'Priya',
					shipped_by: null,
					shipped_by_logo: null,
					...dashboard,
				} as DashboardListItem,
				dropdownOptions: [],
			}),
	})
	for (const name of ['router-link', 'Tooltip', 'Button', 'Dropdown']) {
		app.component(name, {
			props: ['text', 'disabled'],
			render() {
				return h('div', (this as any).$slots.default?.())
			},
		})
	}
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('a dashboard card', () => {
	// @feature dashboard.preview-same-rows
	it('shows the preview the list sends', async () => {
		const html = await card({ preview_image: '/preview', same_rows_for_every_reader: true })
		expect(html).toContain('src="/preview"')
		expect(html).not.toContain(NO_SHARED_PREVIEW)
	})

	// @feature dashboard.preview-same-rows
	it('shows a placeholder that says why where readers see different rows', async () => {
		const html = await card({ preview_image: null, same_rows_for_every_reader: false })
		expect(html).not.toContain('<img')
		expect(html).toContain(`aria-label="${NO_SHARED_PREVIEW.replace("'", '&#39;')}"`)
	})

	// @feature dashboard.preview-same-rows
	it('shows a placeholder with no reason before a shared preview is rendered', async () => {
		const html = await card({ preview_image: null, same_rows_for_every_reader: true })
		expect(html).not.toContain('<img')
		expect(html).not.toContain('no shared preview')
	})
})
