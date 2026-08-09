import { describe, expect, it } from 'vitest'
import { breakdownChart } from './breakdown_chart'

// What a breakdown level draws itself as, and nothing about how it draws it.
// The shape is the answer's own reading of the Dimension, so these read the flag
// the server sent and assert on the config that comes out of it.

const columns = [
	{ name: 'due_date', type: 'Date' as const },
	{ name: 'region', type: 'String' as const },
	{ name: 'count', type: 'Integer' as const },
]

const axis = (chart: any) => chart.config.x_axis.dimension

describe('the chart a breakdown level draws itself as', () => {
	it('ranks an unordered Dimension as a Row chart, with every bar labelled', () => {
		const chart = breakdownChart('region', 'count', { columns, ordered: false })
		expect(chart.chart_type).toBe('Row')
		expect((chart.config as any).y_axis.show_data_labels).toBe(true)
	})

	it('reads a Dimension with an order of its own as a Line chart', () => {
		// the level came back in that order, cut to the latest stretch: a ranking's
		// shape would say the bars could be rearranged, and they cannot
		const chart = breakdownChart('due_date', 'count', {
			columns,
			ordered: true,
			granularity: 'month',
		})
		expect(chart.chart_type).toBe('Line')
		expect((chart.config as any).y_axis.show_data_labels).toBe(false)
	})

	it('draws the axis at the grain the level was grouped by', () => {
		const chart = breakdownChart('due_date', 'count', {
			columns,
			ordered: true,
			granularity: 'week',
		})
		expect(axis(chart)).toMatchObject({ column_name: 'due_date', granularity: 'week' })
	})

	it('never decides the shape from the column type, only from the answer', () => {
		// a date the server ranked — because the segment's span had no order worth
		// reading — is a ranking, and drawing it as a line would invent one
		expect(breakdownChart('due_date', 'count', { columns, ordered: false }).chart_type).toBe(
			'Row',
		)
	})

	it('measures the column the click landed on', () => {
		const chart = breakdownChart('region', 'count', { columns })
		expect((chart.config as any).y_axis.series[0].measure.measure_name).toBe('count')
	})
})
