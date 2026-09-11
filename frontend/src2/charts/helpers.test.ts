import { describe, expect, it } from 'vitest'
import { handleOldHideFromChart } from './helpers'

// `hide_from_chart` drew a series at zero opacity and kept it out of the legend,
// which left its value reaching the tooltip and nothing else. `tooltip.measures`
// says the same thing directly, so the flag moves there on load.

const measure = (name: string) => ({
	measure_name: name,
	column_name: name,
	data_type: 'Decimal',
	aggregation: 'sum',
})

function config(series: any[], tooltip?: any[]) {
	return {
		x_axis: { dimension: { dimension_name: 'region' } },
		y_axis: { series },
		...(tooltip ? { tooltip: { measures: tooltip } } : {}),
	} as any
}

describe('a series the author hid from the chart', () => {
	it('becomes a tooltip Measure', () => {
		const migrated = handleOldHideFromChart(
			config([
				{ measure: measure('revenue') },
				{ measure: measure('orders'), hide_from_chart: true },
			]),
		)
		expect(migrated.y_axis.series.map((s: any) => s.measure.measure_name)).toEqual(['revenue'])
		expect(migrated.tooltip.measures.map((m: any) => m.measure_name)).toEqual(['orders'])
	})

	it('keeps the flag, so the same config migrates the same way twice', () => {
		const once = handleOldHideFromChart(
			config([
				{ measure: measure('revenue') },
				{ measure: measure('orders'), hide_from_chart: true },
			]),
		)
		const twice = handleOldHideFromChart(once)
		expect(twice.tooltip.measures.map((m: any) => m.measure_name)).toEqual(['orders'])
	})

	it('joins the tooltip Measures already there rather than replacing them', () => {
		const migrated = handleOldHideFromChart(
			config(
				[
					{ measure: measure('revenue') },
					{ measure: measure('orders'), hide_from_chart: true },
				],
				[measure('refunds')],
			),
		)
		expect(migrated.tooltip.measures.map((m: any) => m.measure_name)).toEqual([
			'refunds',
			'orders',
		])
	})

	it('is not written twice when the tooltip already names it', () => {
		const migrated = handleOldHideFromChart(
			config(
				[
					{ measure: measure('revenue') },
					{ measure: measure('orders'), hide_from_chart: true },
				],
				[measure('orders')],
			),
		)
		expect(migrated.tooltip.measures.map((m: any) => m.measure_name)).toEqual(['orders'])
	})
})

describe('a config with nothing to migrate', () => {
	it('is left alone when no series is hidden', () => {
		const before = config([{ measure: measure('revenue') }])
		expect(handleOldHideFromChart(before).tooltip).toBeUndefined()
	})

	// Moving every series would leave the adapter no value column to plot, and it
	// draws nothing at all rather than an empty plot.
	it('is left alone when every series is hidden', () => {
		const before = config([
			{ measure: measure('revenue'), hide_from_chart: true },
			{ measure: measure('orders'), hide_from_chart: true },
		])
		const after = handleOldHideFromChart(before)
		expect(after.tooltip).toBeUndefined()
		expect(after.y_axis.series).toHaveLength(2)
	})

	it('leaves a chart type that carries no series untouched', () => {
		const before = { label_column: {}, value_column: {} } as any
		expect(handleOldHideFromChart(before)).toBe(before)
	})
})
