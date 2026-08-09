import { SankeyChart } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import { sankeyChart, type SankeyChartSpec } from './fixtures'
import { adaptChart } from './index'

function adapt(spec: SankeyChartSpec) {
	const filler = adaptChart(sankeyChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

describe('a sankey', () => {
	it('names the node a flow leaves, the one it arrives at, and what runs along it', () => {
		const input = sankeyChart({
			title: 'Traffic to category',
			source: 'traffic_source',
			target: 'category',
			measure: 'revenue',
		})
		const { component, props } = adaptChart(input)!

		expect(component).toBe(SankeyChart)
		expect(props.title).toBe('Traffic to category')
		expect(props.source).toBe('traffic_source')
		expect(props.target).toBe('category')
		expect(props.value).toBe('revenue')
		// The server groups by the source and the target, so a row is a flow.
		expect(props.data).toBe(input.result.rows)
	})

	it('runs the flow the way the Chart asked, and pins its nodes where it said', () => {
		const props = adapt({
			source: 'traffic_source',
			target: 'category',
			measure: 'revenue',
			orient: 'vertical',
			nodeAlign: 'left',
		}).props
		expect(props.orient).toBe('vertical')
		expect(props.nodeAlign).toBe('left')
	})

	it('draws nothing until the Chart names all three columns', () => {
		expect(
			adaptChart(sankeyChart({ source: '', target: 'category', measure: 'revenue' })),
		).toBeUndefined()
		expect(
			adaptChart(sankeyChart({ source: 'traffic_source', target: '', measure: 'revenue' })),
		).toBeUndefined()
		expect(
			adaptChart(sankeyChart({ source: 'traffic_source', target: 'category', measure: '' })),
		).toBeUndefined()
	})
})

describe('drilling into a flow', () => {
	it('names the value column and the row the band was drawn from', () => {
		const input = sankeyChart({
			source: 'traffic_source',
			target: 'category',
			measure: 'revenue',
		})
		const row = input.result.rows[1]

		expect(
			adaptChart(input)!.drillDown!.linkClick({
				source: 'Email',
				target: 'Tops',
				value: 20,
				row,
			}),
		).toEqual({ column: 'revenue', row })
	})
})
