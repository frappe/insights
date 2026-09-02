import { describe, expect, it } from 'vitest'
import { breakdownChart, breakdownPlot, type BreakdownAnswer } from './breakdown_chart'

// What a breakdown level draws itself as, and nothing about how it draws it.
// The shape is the answer's own reading, so these build answers and assert on
// the shape that comes out — never on a column type read directly.

const dated = [
	{ name: 'due_date', type: 'Date' as const },
	{ name: 'count', type: 'Integer' as const },
]

const ranked = [
	{ name: 'region', type: 'String' as const },
	{ name: 'count', type: 'Integer' as const },
]

/** `n` groups of the named column, each worth `value`. */
function rows(column: string, n: number, value = 10) {
	return Array.from({ length: n }, (_, i) => ({ [column]: `g${i}`, count: value }))
}

function answer(over: Partial<BreakdownAnswer> = {}): BreakdownAnswer {
	return { columns: ranked, rows: rows('region', 10), ...over }
}

const config = (chart: ReturnType<typeof breakdownChart>) => chart.config as any

describe('the shape a breakdown level draws itself as', () => {
	it('ranks an unordered Dimension as a Row chart', () => {
		expect(breakdownPlot('region', answer()).chart_type).toBe('Row')
	})

	it('reads a Dimension with an order of its own as a Line chart', () => {
		// the level came back in that order, cut to the latest stretch: a ranking's
		// shape would say the buckets could be rearranged, and they cannot
		const stretch = answer({ columns: dated, rows: rows('due_date', 12), ordered: true })
		expect(breakdownPlot('due_date', stretch).chart_type).toBe('Line')
	})

	it('draws a short stretch as bars, because a few points trace no shape', () => {
		const short = answer({ columns: dated, rows: rows('due_date', 3), ordered: true })
		expect(breakdownPlot('due_date', short).chart_type).toBe('Bar')
	})

	it('never decides the shape from the column type, only from the answer', () => {
		// a date the server ranked — because the segment's span had no order worth
		// reading — is a ranking, and drawing it as a line would invent one
		const date = answer({ columns: dated, rows: rows('due_date', 12), ordered: false })
		expect(breakdownPlot('due_date', date).chart_type).toBe('Row')
	})

	it('falls back to the grid when nothing in the answer holds a number', () => {
		const text = answer({
			columns: [
				{ name: 'region', type: 'String' },
				{ name: 'owner', type: 'String' },
			],
			rows: [{ region: 'North', owner: 'sam' }],
		})
		expect(breakdownPlot('region', text).chart_type).toBe('Table')
	})
})

describe('a ranking read as parts of one whole', () => {
	const whole = (over: Partial<BreakdownAnswer> = {}) =>
		answer({ rows: rows('region', 4), additive: true, total_row_count: 4, ...over })

	it('draws few additive groups that all came back as a Donut', () => {
		expect(breakdownPlot('region', whole()).chart_type).toBe('Donut')
	})

	it('will not divide a whole made of averages', () => {
		// four regions' average order values do not add up to anything
		expect(breakdownPlot('region', whole({ additive: false })).chart_type).toBe('Row')
	})

	it('will not draw a ring out of the biggest few of many groups', () => {
		// the slices would not close: 40 groups exist and 4 are shown
		expect(breakdownPlot('region', whole({ total_row_count: 40 })).chart_type).toBe('Row')
	})

	it('will not draw a negative slice', () => {
		const refunds = whole({ rows: [...rows('region', 3), { region: 'g3', count: -5 }] })
		expect(breakdownPlot('region', refunds).chart_type).toBe('Row')
	})

	it('will not put more slices on a ring than a reader can tell apart', () => {
		const many = whole({ rows: rows('region', 9), total_row_count: 9 })
		expect(breakdownPlot('region', many).chart_type).toBe('Row')
	})

	it('divides one total, so several measures are several totals', () => {
		const two = whole({
			columns: [...ranked, { name: 'amount', type: 'Decimal' }],
			rows: rows('region', 4).map((row) => ({ ...row, amount: 5 })),
		})
		expect(breakdownPlot('region', two).chart_type).toBe('Row')
	})
})

describe('the marks a level labels', () => {
	it('labels bars, which are read as values', () => {
		expect(breakdownPlot('region', answer()).labels).toBe(true)
	})

	it('never labels a line, which is read as a shape', () => {
		const stretch = answer({ columns: dated, rows: rows('due_date', 12), ordered: true })
		expect(breakdownPlot('due_date', stretch).labels).toBe(false)
	})

	it('drops the labels once there are more marks than they fit on', () => {
		const wide = answer({
			columns: [...ranked, { name: 'amount', type: 'Decimal' }],
			rows: rows('region', 20).map((row) => ({ ...row, amount: 5 })),
		})
		expect(breakdownPlot('region', wide).labels).toBe(false)
	})
})

describe('the config a shape is drawn from', () => {
	it('draws the axis at the grain the level was grouped by', () => {
		const chart = breakdownChart(
			'due_date',
			answer({ columns: dated, rows: rows('due_date', 12), ordered: true, granularity: 'week' }),
		)
		expect(config(chart).x_axis.dimension).toMatchObject({
			column_name: 'due_date',
			granularity: 'week',
		})
	})

	it('measures every numeric column the answer carried', () => {
		// a click on a number card names no measure and keeps all of them
		const chart = breakdownChart(
			'region',
			answer({
				columns: [...ranked, { name: 'amount', type: 'Decimal' }],
				rows: rows('region', 3).map((row) => ({ ...row, amount: 5 })),
			}),
		)
		expect(config(chart).y_axis.series.map((s: any) => s.measure.measure_name)).toEqual([
			'count',
			'amount',
		])
	})

	it('names the one total a ring divides', () => {
		const chart = breakdownChart(
			'region',
			answer({ rows: rows('region', 4), additive: true, total_row_count: 4 }),
		)
		expect(config(chart).label_column.column_name).toBe('region')
		expect(config(chart).value_column.measure_name).toBe('count')
	})

	it('puts every column of a fallback grid on it', () => {
		const text = answer({
			columns: [
				{ name: 'region', type: 'String' },
				{ name: 'owner', type: 'String' },
			],
			rows: [{ region: 'North', owner: 'sam' }],
		})
		expect(config(breakdownChart('region', text)).rows[0].column_name).toBe('region')
	})
})
