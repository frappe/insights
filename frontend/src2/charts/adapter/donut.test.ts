import { DonutChart } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import { donutChart, type DonutChartSpec } from './fixtures'
import { adaptChart } from './index'

// Props, never an echarts option: what the ring is drawn from is v2's concern.

function adapt(spec: DonutChartSpec) {
	const filler = adaptChart(donutChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const propsOf = (spec: DonutChartSpec) => adapt(spec).props

describe('a donut', () => {
	// @feature charts.type-donut
	it('names the column the segments are read from and the one they are sized by', () => {
		const { component, props } = adapt({
			title: 'Revenue share',
			category: 'category',
			measure: 'revenue',
		})
		expect(component).toBe(DonutChart)
		expect(props.title).toBe('Revenue share')
		expect(props.category).toBe('category')
		expect(props.value).toBe('revenue')
	})

	// @feature charts.type-donut
	it('hands the result over as it stands, already grouped and already sorted', () => {
		const input = donutChart({
			category: 'category',
			measure: 'revenue',
			slices: [
				{ label: 'Tops', value: 30 },
				{ label: 'Jeans', value: 20 },
			],
		})
		expect(adaptChart(input)?.props.data).toBe(input.result.rows)
	})

	// @feature charts.donut-max-slices
	it('caps the segments and leaves the ring to collapse the tail', () => {
		// v2 sums everything past the cap into one segment itself. Capping here as
		// well would collapse a tail that is already a tail.
		expect(propsOf({ category: 'category', measure: 'revenue', maxSlices: 8 }).maxSlices).toBe(
			8,
		)
	})

	// @feature charts.donut-max-slices
	it('leaves the cap to the ring when the Chart sets none', () => {
		expect(propsOf({ category: 'category', measure: 'revenue' }).maxSlices).toBeUndefined()
	})

	// @feature charts.donut-inline-labels
	it('prints the shares beside the ring when the Chart asks for them', () => {
		const props = propsOf({ category: 'category', measure: 'revenue', inlineLabels: true })
		expect(props.showDataLabels).toBe(true)
	})

	// @feature charts.donut-inline-labels
	it('says nothing about where the legend sits', () => {
		// Legend placement is the library's, so the stored side is dropped rather
		// than carried under another name.
		const props = propsOf({
			category: 'category',
			measure: 'revenue',
			legendPosition: 'right',
		})
		expect(Object.keys(props)).toEqual(['title', 'data', 'category', 'value', 'format'])
	})

	// @feature charts.type-donut
	it('draws nothing until the Chart names both columns', () => {
		expect(adaptChart(donutChart({ category: '', measure: 'revenue' }))).toBeUndefined()
		expect(adaptChart(donutChart({ category: 'category', measure: '' }))).toBeUndefined()
	})
})

describe('drilling into a segment', () => {
	// @feature charts.drill-segment
	it('names the value column and the row the segment was drawn from', () => {
		const input = donutChart({ category: 'category', measure: 'revenue' })
		const row = input.result.rows[1]

		expect(
			adaptChart(input)!.drillDown!.select({
				name: 'South',
				value: 20,
				percent: 40,
				rows: [row],
			}),
		).toEqual({ column: 'revenue', row })
	})

	// @feature charts.drill-segment
	it('drills into nothing from the tail, which stands for several rows', () => {
		const input = donutChart({ category: 'category', measure: 'revenue' })

		expect(
			adaptChart(input)!.drillDown!.select({
				name: 'Others',
				value: 50,
				percent: 100,
				rows: input.result.rows,
			}),
		).toBeUndefined()
	})
})
