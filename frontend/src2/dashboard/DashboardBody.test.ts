import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'

vi.mock('../router', () => ({ default: { push() {}, resolve: () => ({ href: '/' }) } }))

import DashboardBody from './DashboardBody.vue'

async function emptyDashboard(builder?: Record<string, any>) {
	const dashboard = reactive({ title: 'New', items: [], loading: false, builder })
	const app = createSSRApp({
		render: () => h(DashboardBody as any, { dashboard, grid: 'div', cell: 'div' }),
	})
	app.component('Button', {
		props: ['label'],
		render() {
			return h('span', (this as any).label)
		},
	})
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('an empty dashboard', () => {
	// @feature dashboard.create-add-chart
	it('offers its author a chart to add before editing starts', async () => {
		const html = await emptyDashboard({ editing: false, pickCharts() {} })

		expect(html).toContain('Add a chart')
		expect(html).not.toContain('This dashboard is empty')
	})

	// @feature dashboard.create-add-chart
	it('tells a reader it is empty', async () => {
		expect(await emptyDashboard()).toContain('This dashboard is empty')
	})
})
