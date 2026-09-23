import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { makeChartRead } from './chart_view'
import ChartView from './ChartView.vue'

// What a card offers a reader over the chart it draws. Every view surface draws
// its card here — the dashboard page, the public link — so an act missing from
// this component is missing from all of them.

function card(chart_type: string, slots: Record<string, () => any> = {}) {
	const read = makeChartRead({
		doc: { name: 'chart-1', title: 'Revenue', chart_type, config: {} as any },
		fetchData: () => Promise.resolve({ columns: [], rows: [] }),
		fetchDrillData: () => Promise.reject(new Error('not asked')),
	})
	const app = createSSRApp({ render: () => h(ChartView, { chart: read }, slots) })
	// the app registers frappe-ui's components globally; this render is one card
	// and does not need them resolved
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('a chart card a reader is given', () => {
	// @feature charts.expand
	it('offers the picture full-size, except where the picture is a reading', async () => {
		expect(await card('Bar')).toContain('aria-label="Expand"')
		// a Number card is a reading rather than a plot, and has nothing more to show
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

		// the host is told whether the acts are hidden behind a hover, because the
		// group that reveals them is the card and the expanded dialog is outside it
		expect(scope).toEqual({ expanded: false })
		// a hover act waits with Expand, in the card's own group. A bare
		// `group-hover` would answer to the grid cell and its gutter instead.
		const hidden = html.slice(html.indexOf('w-0 overflow-hidden'))
		expect(hidden).toContain('group-hover/card:w-auto')
		expect(hidden.indexOf('Edit Chart')).toBeLessThan(hidden.indexOf('aria-label="Expand"'))
	})
})
