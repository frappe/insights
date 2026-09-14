import { HeatmapChart } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import { heatmapChart, type HeatmapChartSpec } from './fixtures'
import { adaptChart } from './index'

function adapt(spec: HeatmapChartSpec) {
	const filler = adaptChart(heatmapChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

describe('a heatmap', () => {
	it('names the two columns the grid is cut by, and what colors a cell', () => {
		const input = heatmapChart({
			title: 'Orders by day and hour',
			x: 'day',
			y: 'hour',
			measure: 'orders',
		})
		const { component, props } = adaptChart(input)!

		expect(component).toBe(HeatmapChart)
		expect(props.title).toBe('Orders by day and hour')
		expect(props.x).toBe('day')
		expect(props.y).toBe('hour')
		expect(props.value).toBe('orders')
		// The server groups by both dimensions, so a row is a cell.
		expect(props.data).toBe(input.result.rows)
	})

	it('prints the numbers and scales the color the way the Chart asked', () => {
		const props = adapt({
			x: 'day',
			y: 'hour',
			measure: 'orders',
			showValues: true,
			palette: 'diverging',
			min: -10,
			max: 50,
		}).props
		expect(props.showValues).toBe(true)
		expect(props.palette).toBe('diverging')
		expect(props.min).toBe(-10)
		expect(props.max).toBe(50)
	})

	it('leaves the scale to the data until the Chart pins an end of it', () => {
		const props = adapt({ x: 'day', y: 'hour', measure: 'orders' }).props
		expect(props.min).toBeUndefined()
		expect(props.max).toBeUndefined()
		expect(props.showValues).toBeUndefined()
	})

	it('prints a date cut at the grain it was grouped by', () => {
		// A grid cuts by categories, so neither axis is the time axis that prints
		// an axis chart's dates. The grain has to come across as a formatter.
		const props = adapt({
			x: { name: 'created_at', type: 'Datetime', granularity: 'month' },
			y: 'category',
			measure: 'revenue',
		}).props

		expect(props.xAxis.format('2024-03-01 00:00:00')).toBe('Mar 2024')
		expect(props.yAxis).toBeUndefined()
	})

	it('leaves a plain category to print itself', () => {
		const props = adapt({ x: 'day', y: 'hour', measure: 'orders' }).props
		expect(props.xAxis).toBeUndefined()
		expect(props.yAxis).toBeUndefined()
	})

	it('draws nothing until the Chart names all three columns', () => {
		expect(adaptChart(heatmapChart({ x: '', y: 'hour', measure: 'orders' }))).toBeUndefined()
		expect(adaptChart(heatmapChart({ x: 'day', y: '', measure: 'orders' }))).toBeUndefined()
		expect(adaptChart(heatmapChart({ x: 'day', y: 'hour', measure: '' }))).toBeUndefined()
	})
})

describe('drilling into a cell', () => {
	it('names the value column and the row the cell was drawn from', () => {
		const input = heatmapChart({ x: 'day', y: 'hour', measure: 'orders' })
		const row = input.result.rows[1]

		expect(
			adaptChart(input)!.drillDown!.select({
				x: 'Mon',
				y: 'Evening',
				value: 12,
				row,
			}),
		).toEqual({ column: 'orders', row })
	})
})
