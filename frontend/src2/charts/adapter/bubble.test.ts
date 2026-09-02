import { ScatterChart } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import { bubbleChart, type BubbleChartSpec } from './fixtures'
import { adaptChart } from './index'

function adapt(spec: BubbleChartSpec) {
	const filler = adaptChart(bubbleChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const propsOf = (spec: BubbleChartSpec) => adapt(spec).props

describe('a bubble chart', () => {
	it('reads one Measure against another, sized and named by two more columns', () => {
		const input = bubbleChart({
			title: 'Revenue vs profit',
			x: 'revenue',
			y: 'profit',
			size: 'items',
			label: 'category',
			group: 'department',
		})
		const { component, props } = adaptChart(input)!

		expect(component).toBe(ScatterChart)
		expect(props.title).toBe('Revenue vs profit')
		expect(props.x).toBe('revenue')
		expect(props.y).toBe('profit')
		expect(props.size).toBe('items')
		expect(props.label).toBe('category')
		// Coloring the points by a Dimension is grouping them by it, which is
		// what a series is.
		expect(props.series).toBe('department')
		expect(props.data).toBe(input.result.rows)
	})

	it('names only the columns the Chart filled', () => {
		const props = propsOf({ x: 'revenue', y: 'profit' })
		expect(props.size).toBeUndefined()
		expect(props.label).toBeUndefined()
		expect(props.series).toBeUndefined()
	})

	it('prints each point’s own name beside it when the Chart asks', () => {
		// The name column, not a measure: both measures are on the axes already.
		const props = propsOf({ x: 'revenue', y: 'profit', label: 'category', dataLabels: true })
		expect(props.showDataLabels).toBe(true)
		expect(props.label).toBe('category')
	})

	it('prints none by default', () => {
		expect(propsOf({ x: 'revenue', y: 'profit', label: 'category' }).showDataLabels).toBeUndefined()
	})

	it('draws nothing until the Chart names both Measures', () => {
		expect(adaptChart(bubbleChart({ x: '', y: 'profit' }))).toBeUndefined()
		expect(adaptChart(bubbleChart({ x: 'revenue', y: '' }))).toBeUndefined()
	})
})

describe('the quadrant dividers', () => {
	it('cuts the plot in four with a rule on each scale', () => {
		// Both axes of a scatter are value axes, so the vertical rule sits at a
		// number on the horizontal scale rather than at a category.
		expect(
			propsOf({
				x: 'revenue',
				y: 'profit',
				quadrants: { x: 255909, y: 138980 },
			}).referenceLines,
		).toEqual([
			{ axis: 'x', value: 255909, dashed: true },
			{ axis: 'y', value: 138980, dashed: true },
		])
	})

	it('draws only the rule the Chart set a value for', () => {
		expect(propsOf({ x: 'revenue', y: 'profit', quadrants: { x: 100 } }).referenceLines).toEqual(
			[{ axis: 'x', value: 100, dashed: true }],
		)
	})

	it('computes no divider of its own', () => {
		// Nothing derives a midpoint from the data, before or after the swap: the
		// line sits where the author put it, or nowhere.
		expect(propsOf({ x: 'revenue', y: 'profit', quadrants: {} }).referenceLines).toBeUndefined()
	})

	it('draws none when the Chart keeps the values but switched them off', () => {
		expect(
			propsOf({ x: 'revenue', y: 'profit', quadrants: { x: 100, y: 50, shown: false } })
				.referenceLines,
		).toBeUndefined()
	})
})

describe('drilling into a point', () => {
	it('names the vertical Measure and the row behind the point', () => {
		const input = bubbleChart({ x: 'revenue', y: 'profit', group: 'department' })
		const row = input.result.rows[1]

		expect(
			adaptChart(input)!.drillDown!.select({
				seriesName: 'Men',
				x: 30,
				y: 40,
				size: null,
				row,
			}),
		).toEqual({ column: 'profit', row })
	})
})
