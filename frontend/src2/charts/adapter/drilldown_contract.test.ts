import { describe, expect, it } from 'vitest'
import {
	axisChart,
	bubbleChart,
	donutChart,
	funnelChart,
	heatmapChart,
	mapChart,
	sankeyChart,
	tableChart,
} from './fixtures'
import { adaptChart } from './index'
import type { ChartAdapterInput } from './types'

// Other suites call each resolver by the name it registered under, so a renamed
// event breaks nothing they assert. This suite checks each key against the
// component that emits it.

const drillable: Array<[string, ChartAdapterInput]> = [
	['Bar', axisChart({ type: 'Bar', dimension: 'month', measures: ['revenue'] })],
	['Line', axisChart({ type: 'Line', dimension: 'month', measures: ['revenue'] })],
	['Donut', donutChart({ category: 'region', measure: 'revenue' })],
	['Funnel', funnelChart({ dimension: 'stage', measure: 'count' })],
	['Sankey', sankeyChart({ source: 'from', target: 'to', measure: 'amount' })],
	['Heatmap', heatmapChart({ x: 'day', y: 'hour', measure: 'orders' })],
	['Bubble', bubbleChart({ x: 'cost', y: 'revenue', size: 'orders' })],
	['Map', mapChart({ regions: [{ region: 'India', value: 30 }] })],
	['Table', tableChart({ rows: ['region'], values: ['revenue'] })],
]

describe.each(drillable)('the %s chart', (_type, input) => {
	// @feature charts.drill-segment
	it('names an event its component declares', () => {
		const filler = adaptChart(input)
		if (!filler) throw new Error('the adapter drew nothing for this Chart')
		// every chart listed here is drillable, so a missing block is the failure
		// this test exists to catch
		expect(filler.drillDown).toBeDefined()

		// `<script setup>` compiles `defineEmits` down to this, for a frappe-ui
		// chart and an Insights one alike. A component declaring none has nothing
		// to check against, which fails here rather than passing on an empty list.
		const declared = (filler.component as { emits?: string[] }).emits

		expect(declared).toEqual(expect.arrayContaining(Object.keys(filler.drillDown!)))
	})
})
