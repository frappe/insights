import { describe, expect, it } from 'vitest'
import {
	axisChart,
	bubbleChart,
	donutChart,
	funnelChart,
	heatmapChart,
	loadedComponent,
	mapChart,
	sankeyChart,
	tableChart,
} from './fixtures'
import { ADAPTERS, adaptChart, rendersOwnCards } from './index'
import type { ChartAdapterInput } from './types'

// Every type the chrome heads prints the Chart's description under its title.
// A Number chart renders its own cards, which have no such line.

const DESCRIPTION = 'Trials started this month'

const headed: Array<[string, ChartAdapterInput]> = [
	['Bar', axisChart({ type: 'Bar', dimension: 'month', measures: ['revenue'] })],
	['Line', axisChart({ type: 'Line', dimension: 'month', measures: ['revenue'] })],
	['Row', axisChart({ type: 'Row', dimension: 'month', measures: ['revenue'] })],
	['Donut', donutChart({ category: 'region', measure: 'revenue' })],
	['Funnel', funnelChart({ dimension: 'stage', measure: 'count' })],
	['Bubble', bubbleChart({ x: 'cost', y: 'revenue', size: 'orders' })],
	['Sankey', sankeyChart({ source: 'from', target: 'to', measure: 'amount' })],
	['Heatmap', heatmapChart({ x: 'day', y: 'hour', measure: 'orders' })],
	['Map', mapChart({ regions: [{ region: 'India', value: 30 }] })],
	['Table', tableChart({ rows: ['region'], values: ['revenue'] })],
]

// @feature charts.description-and-info
it('lists every type the chrome heads', () => {
	const types = Object.keys(ADAPTERS).filter((type) => !rendersOwnCards(type))
	expect(headed.map(([type]) => type).sort()).toEqual(types.sort())
})

describe.each(headed)('the %s chart', (_type, input) => {
	// @feature charts.description-and-info
	it('hands its description to a component that prints it as the subtitle', async () => {
		const filler = adaptChart({ ...input, description: DESCRIPTION })
		if (!filler) throw new Error('the adapter rendered nothing for this Chart')
		expect(filler.props.subtitle).toBe(DESCRIPTION)

		const props = ((await loadedComponent(filler.component)) as { props?: object }).props
		expect(Object.keys(props || {})).toContain('subtitle')
	})
})
