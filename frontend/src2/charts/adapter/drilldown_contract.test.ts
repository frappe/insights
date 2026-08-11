import { describe, expect, it } from 'vitest'
import {
	axisChart,
	bubbleChart,
	donutChart,
	funnelChart,
	mapChart,
	sankeyChart,
	tableChart,
} from './fixtures'
import { adaptChart } from './index'
import type { ChartAdapterInput } from './types'

// A drill-down resolver is keyed by the name of the event that carries the
// click, and nothing else ever names it: the chrome binds the keys blind, and
// every other suite calls the resolver by the same name it registered under. So
// a chart renaming its event takes the drill-down down with it and every test
// stays green — which is how the v2 charts going from `datapointClick` to
// `select` reached a release. This is the one place the key is read against the
// component that has to emit it.

const drillable: Array<[string, ChartAdapterInput]> = [
	['Bar', axisChart({ type: 'Bar', dimension: 'month', measures: ['revenue'] })],
	['Line', axisChart({ type: 'Line', dimension: 'month', measures: ['revenue'] })],
	['Donut', donutChart({ category: 'region', measure: 'revenue' })],
	['Funnel', funnelChart({ dimension: 'stage', measure: 'count' })],
	['Sankey', sankeyChart({ source: 'from', target: 'to', measure: 'amount' })],
	['Bubble', bubbleChart({ x: 'cost', y: 'revenue', size: 'orders' })],
	['Map', mapChart({ regions: [{ region: 'India', value: 30 }] })],
	['Table', tableChart({ rows: ['region'], values: ['revenue'] })],
]

describe.each(drillable)('the %s chart', (_type, input) => {
	it('names an event its component declares', () => {
		const filler = adaptChart(input)
		if (!filler) throw new Error('the adapter drew nothing for this Chart')
		if (!filler.drillDown) return

		// `<script setup>` compiles `defineEmits` down to this, for a frappe-ui
		// chart and an Insights one alike.
		const declared = (filler.component as { emits?: string[] }).emits ?? []

		for (const event of Object.keys(filler.drillDown)) {
			expect(declared).toContain(event)
		}
	})
})
