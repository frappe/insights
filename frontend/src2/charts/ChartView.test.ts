import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { makeChartRead } from './chart_view'
import ChartView from './ChartView.vue'

// Every View renders its card with this component: the dashboard page, the
// public link. An action missing here is missing from all of them.

function card(chart_type: string, slots: Record<string, () => any> = {}) {
	const read = makeChartRead({
		doc: { name: 'chart-1', title: 'Revenue', chart_type, config: {} as any },
		fetchData: () => Promise.resolve({ columns: [], rows: [] }),
		fetchDrillData: () => Promise.reject(new Error('not asked')),
	})
	const app = createSSRApp({ render: () => h(ChartView, { chart: read }, slots) })
	// The app registers frappe-ui components globally. This test does not, so it
	// silences the warnings for unresolved components.
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('a chart card a reader is given', () => {
	// @feature charts.expand
	it('offers the picture full-size, except where the picture is a reading', async () => {
		expect(await card('Bar')).toContain('aria-label="Expand"')
		// A Number card has no plot, so a larger view shows nothing more.
		expect(await card('Number')).not.toContain('aria-label="Expand"')
	})

	// @feature charts.expand
	it('reveals a host act on hover from the card, and says when it is expanded', async () => {
		let scope: { expanded: boolean } | undefined
		const html = await card('Bar', {
			actions: (props: any) => {
				scope = props
				return h('span', 'the host act')
			},
			hoverActions: () => h('span', { 'aria-label': 'Edit Chart' }, 'edit'),
		})

		// Hover on the card shows the actions. The expanded dialog is outside the
		// card, so the host must know when the chart is expanded.
		expect(scope).toEqual({ expanded: false })
		// A bare `group-hover` would also react to the grid cell and its gutter,
		// so hover actions use the card's named group.
		const hidden = html.slice(html.indexOf('w-0 overflow-hidden'))
		expect(hidden).toContain('group-hover/card:w-auto')
		expect(hidden.indexOf('Edit Chart')).toBeLessThan(hidden.indexOf('aria-label="Expand"'))
	})
})
