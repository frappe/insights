import { BarChart, LineChart } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import { adaptChart } from './index'
import { axisChart, type AxisChartSpec } from './fixtures'

// Everything here asserts on the props a chart is handed. What echarts is asked
// to draw from them is v2's business, and v2 tests it.

function adapt(spec: AxisChartSpec) {
	const filler = adaptChart(axisChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const propsOf = (spec: AxisChartSpec) => adapt(spec).props

describe('the three axis types', () => {
	it('draws a Bar Chart as a bar chart, its Measures in a list', () => {
		const { component, props } = adapt({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue'],
		})
		expect(component).toBe(BarChart)
		expect(props.x).toBe('region')
		// A list even for one Measure: wide data is the one shape, not the shape
		// a split falls back to.
		expect(props.y).toEqual(['revenue'])
		expect(props.horizontal).toBeUndefined()
	})

	it('draws a Line Chart as a line chart', () => {
		const filler = adapt({ type: 'Line', dimension: 'region', measures: ['revenue'] })
		expect(filler.component).toBe(LineChart)
		expect(filler.props.horizontal).toBeUndefined()
	})

	it('draws a Row Chart as a bar chart lying down', () => {
		const filler = adapt({ type: 'Row', dimension: 'region', measures: ['revenue'] })
		expect(filler.component).toBe(BarChart)
		expect(filler.props.horizontal).toBe(true)
	})

	it('hands the result over as it stands, in the order it arrived', () => {
		// The category order is the chart's reading of the data, and a row chart
		// reads it top down. Both belong to the renderer, so nothing is sorted or
		// reversed on the way in.
		const spec: AxisChartSpec = {
			type: 'Row',
			dimension: { name: 'order_date', type: 'Date', granularity: 'month' },
			measures: ['revenue'],
			categories: ['2026-02-01', '2026-01-01'],
		}
		const input = axisChart(spec)
		expect(adaptChart(input)?.props.data).toBe(input.result.rows)
		expect(propsOf(spec).data.map((row: any) => row.order_date)).toEqual([
			'2026-02-01',
			'2026-01-01',
		])
	})

	it('draws nothing until the Chart names a Dimension and the result holds a number', () => {
		expect(adaptChart(axisChart({ type: 'Bar', dimension: '', measures: ['revenue'] }))).toBeUndefined()
		expect(adaptChart(axisChart({ type: 'Bar', dimension: 'region', measures: [] }))).toBeUndefined()
	})
})

describe('the category axis', () => {
	it('reads a text Dimension as categories', () => {
		expect(propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] }).xAxis).toEqual({
			type: 'category',
		})
	})

	it('reads a date Dimension as a timeline at the grain it was grouped by', () => {
		expect(
			propsOf({
				type: 'Line',
				dimension: { name: 'order_date', type: 'Date', granularity: 'month' },
				measures: ['revenue'],
			}).xAxis,
		).toEqual({ type: 'time', timeGrain: 'month' })
	})

	it('prints a fiscal year itself, which a plain calendar has no grain for', () => {
		const xAxis = propsOf({
			type: 'Line',
			dimension: { name: 'order_date', type: 'Date', granularity: 'fiscal_year' },
			measures: ['revenue'],
		}).xAxis
		expect(xAxis.timeGrain).toBeUndefined()
		expect(xAxis.format('2026-06-01')).toMatch(/^FY /)
	})

	it('reads a numeric Dimension as a quantity', () => {
		expect(
			propsOf({
				type: 'Line',
				dimension: { name: 'day_offset', type: 'Integer' },
				measures: ['revenue'],
			}).xAxis,
		).toEqual({ type: 'value' })
	})
})

describe('a split Dimension', () => {
	it('reads its series off the result, which is the only place they are named', () => {
		const props = propsOf({
			type: 'Bar',
			dimension: { name: 'order_date', type: 'Date', granularity: 'month' },
			measures: ['revenue'],
			splitBy: { dimension: 'region', into: ['North', 'South'] },
		})
		expect(props.y).toEqual(['North', 'South'])
		expect(props.x).toBe('order_date')
	})

	it('keeps every Measure of a split apart, one series per column', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'order_date',
				measures: ['revenue', 'margin'],
				splitBy: { dimension: 'region', into: ['North', 'South'] },
			}).y,
		).toEqual([
			'revenue___North',
			'revenue___South',
			'margin___North',
			'margin___South',
		])
	})

	it('takes the collapsed tail as one more series, and caps nothing itself', () => {
		// Ranking the values, rewriting the tail and pivoting all happen in SQL,
		// so "Others" reaches the chart as a column like any other. Capping again
		// here would collapse a tail that is already a tail.
		const props = propsOf({
			type: 'Bar',
			dimension: 'order_date',
			measures: ['revenue'],
			splitBy: { dimension: 'region', into: ['North', 'South', 'Others'] },
		})
		expect(props.y).toEqual(['North', 'South', 'Others'])
		expect(props.maxSeries).toBeUndefined()
		// `series` is v2's long reading and takes one value column. A split can
		// carry several Measures, so only the wide one says what Insights allows.
		expect(props.series).toBeUndefined()
	})
})

describe('the marks a series draws as', () => {
	it('leaves a series that draws the chart’s own mark unstyled', () => {
		expect(
			propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] }).seriesConfig,
		).toBeUndefined()
	})

	it('draws a rate as a line over the bars it is read against', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue', { name: 'margin_rate', mark: 'line' }],
			}).seriesConfig,
		).toEqual({ margin_rate: { type: 'line' } })
	})

	it('draws a line series with a fill under it as an area', () => {
		expect(
			propsOf({
				type: 'Line',
				dimension: 'region',
				measures: ['revenue'],
				area: true,
				smooth: true,
			}).seriesConfig,
		).toEqual({ revenue: { type: 'area', smooth: true } })
	})

	it('lets a Series override what the whole axis asked for', () => {
		expect(
			propsOf({
				type: 'Line',
				dimension: 'region',
				measures: [{ name: 'revenue', color: '#ff0000', dataLabels: true, dataPoints: true }],
			}).seriesConfig,
		).toEqual({
			revenue: { color: '#ff0000', showDataLabels: true, showDataPoints: true },
		})
	})

	it('sends bars standing in front of each other through the escape hatch', () => {
		// Overlap is an instruction to the renderer, not a reading of the data.
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue', 'target'],
			stacked: true,
			overlap: true,
		})
		expect(props.seriesConfig.revenue.echartOptions).toEqual({ barGap: '-100%' })
		expect(props.stacked).toBeUndefined()
	})
})

describe('the second value axis', () => {
	it('measures a Series aligned right against an axis of its own', () => {
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue', { name: 'margin_rate', mark: 'line', axis: 'right' }],
		})
		expect(props.seriesConfig.margin_rate.axis).toBe('y2')
	})

	it('leaves a Series where it stands when it changes axis', () => {
		// The series are drawn and colored in `y` order, so a Series that moved
		// down the list to reach the second axis would change color on the way.
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: [{ name: 'margin_rate', axis: 'right' }, 'revenue'],
		})
		expect(props.y).toEqual(['margin_rate', 'revenue'])
	})

	it('says the same for a row chart, whose one value axis is v2’s business', () => {
		// A row chart runs its value axis across the plot; a second one along the
		// other edge is unreadable, so v2 draws none and reads every series against
		// the primary. The adapter that knew this too was a second place to keep it.
		const props = propsOf({
			type: 'Row',
			dimension: 'region',
			measures: ['revenue', { name: 'margin_rate', axis: 'right' }],
		})
		expect(props.y).toEqual(['revenue', 'margin_rate'])
		expect(props.seriesConfig.margin_rate.axis).toBe('y2')
	})
})

describe('the value axis', () => {
	it('titles the axis only when the Chart asks for the title to show', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue'],
				axisLabel: 'Revenue (₹)',
				min: 0,
				max: 500,
			}).yAxis,
		).toEqual({ title: 'Revenue (₹)', min: 0, max: 500 })
	})

	it('reads stacked shares against the scale they are shares of', () => {
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue', 'refunds'],
			stacked: true,
			normalized: true,
			min: 0,
			max: 500,
		})
		expect(props.stacked).toBe('normalized')
		// The axis carries a percentage now, so a bound set for the raw magnitude
		// would cut the plot off.
		expect(props.yAxis).toBeUndefined()
	})

	it('stacks without normalizing when only the stack was asked for', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue', 'refunds'],
				stacked: true,
			}).stacked,
		).toBe(true)
	})
})

describe('reference lines', () => {
	it('draws a target across the plot, and a marker down it', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue'],
				referenceLines: [
					{ value: 100, label: 'Target', color: '#ff0000', dashed: true },
					{ value: 'South', axis: 'x' },
				],
			}).referenceLines,
		).toEqual([
			{ value: 100, axis: 'y', label: 'Target', color: '#ff0000', dashed: true },
			{ value: 'South', axis: 'x' },
		])
	})

	it('reads a right-aligned line against the axis its series is measured on', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue', { name: 'margin_rate', axis: 'right' }],
				referenceLines: [{ value: 30, align: 'Right' }],
			}).referenceLines,
		).toEqual([{ value: 30, axis: 'y2' }])
	})

	it('drops a line with nothing to sit at', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue'],
				referenceLines: [{ label: 'Target' }, { value: '' }, { value: 0 }],
			}).referenceLines,
		).toEqual([{ value: 0, axis: 'y' }])
	})

	it('adds nothing at all when the Chart has none', () => {
		expect(
			propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] }).referenceLines,
		).toBeUndefined()
	})
})

describe('a series the author switched off', () => {
	it('hands it to the chart as hidden rather than dropping it', () => {
		// It keeps its legend entry, so a reader can switch it back on for a look.
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue', { name: 'refunds', hidden: true }],
		})
		expect(props.y).toEqual(['revenue', 'refunds'])
		expect(props.hiddenSeries).toEqual(['refunds'])
	})

	it('says nothing when every series is drawn', () => {
		expect(
			propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] }).hiddenSeries,
		).toBeUndefined()
	})
})

describe('drilling into a point', () => {
	it('names the column and the row behind it, off the event alone', () => {
		const input = axisChart({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue'],
		})
		const filler = adaptChart(input)!
		const row = input.result.rows[1]

		expect(
			filler.drillDown!.select({
				seriesName: 'revenue',
				dataIndex: 1,
				value: row.revenue,
				row,
			}),
		).toEqual({ column: 'revenue', row })
	})

	// The column a split segment names is a pivoted one, which only the result
	// carries — a drill-down that named the Measure would fail to find it there.
	it('names the pivoted column a split segment was drawn from', () => {
		const input = axisChart({
			type: 'Bar',
			dimension: 'month',
			measures: ['revenue', 'profit'],
			splitBy: { dimension: 'department', into: ['Men', 'Women'] },
		})
		const filler = adaptChart(input)!
		const row = input.result.rows[0]

		for (const series of filler.props.y as string[]) {
			const target = filler.drillDown!.select({
				seriesName: series,
				dataIndex: 0,
				value: row[series],
				row,
			})
			expect(target).toEqual({ column: series, row })
			// what the card then looks the column up by
			expect(input.result.columns.map((c) => c.name)).toContain(target!.column)
		}
	})
})
