import { BarChart, LineChart } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import type { ReferenceLine } from '../../types/chart.types'
import { adaptChart } from './index'
import { axisChart, type AxisChartSpec } from './fixtures'

// Everything here asserts on the props a chart is handed. What echarts draws
// from them is v2's concern, and v2 tests it.

function adapt(spec: AxisChartSpec) {
	const filler = adaptChart(axisChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const propsOf = (spec: AxisChartSpec) => adapt(spec).props

describe('the three axis types', () => {
	// @feature charts.type-bar
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

	// @feature charts.type-line
	it('draws a Line Chart as a line chart', () => {
		const filler = adapt({ type: 'Line', dimension: 'region', measures: ['revenue'] })
		expect(filler.component).toBe(LineChart)
		expect(filler.props.horizontal).toBeUndefined()
	})

	// @feature charts.type-row
	it('draws a Row Chart as a bar chart lying down', () => {
		const filler = adapt({ type: 'Row', dimension: 'region', measures: ['revenue'] })
		expect(filler.component).toBe(BarChart)
		expect(filler.props.horizontal).toBe(true)
	})

	// @feature charts.y-axis-series
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

	// @feature charts.type-bar
	it('draws nothing until the Chart names a Dimension and the result holds a number', () => {
		expect(
			adaptChart(axisChart({ type: 'Bar', dimension: '', measures: ['revenue'] })),
		).toBeUndefined()
		expect(
			adaptChart(axisChart({ type: 'Bar', dimension: 'region', measures: [] })),
		).toBeUndefined()
	})
})

describe('the category axis', () => {
	// @feature charts.x-axis
	it('reads a text Dimension as categories', () => {
		expect(propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] }).xAxis).toEqual({
			type: 'category',
		})
	})

	// @feature charts.x-axis
	it('reads a date Dimension as a timeline at the grain it was grouped by', () => {
		expect(
			propsOf({
				type: 'Line',
				dimension: { name: 'order_date', type: 'Date', granularity: 'month' },
				measures: ['revenue'],
			}).xAxis,
		).toEqual({ type: 'time', timeGrain: 'month' })
	})

	// @feature charts.x-axis
	it('prints a fiscal year itself, which a plain calendar has no grain for', () => {
		const xAxis = propsOf({
			type: 'Line',
			dimension: { name: 'order_date', type: 'Date', granularity: 'fiscal_year' },
			measures: ['revenue'],
		}).xAxis
		expect(xAxis.timeGrain).toBeUndefined()
		expect(xAxis.format('2026-06-01')).toMatch(/^FY /)
	})

	// @feature charts.x-axis
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
	// @feature charts.split-by
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

	// @feature charts.split-by
	it('keeps every Measure of a split apart, one series per column', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'order_date',
				measures: ['revenue', 'margin'],
				splitBy: { dimension: 'region', into: ['North', 'South'] },
			}).y,
		).toEqual(['revenue___North', 'revenue___South', 'margin___North', 'margin___South'])
	})

	// @feature charts.split-by-max-values
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
	// @feature charts.series-type
	it('leaves a series that draws the chart’s own mark unstyled', () => {
		expect(
			propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] }).seriesConfig,
		).toBeUndefined()
	})

	// @feature charts.series-type
	it('draws a rate as a line over the bars it is read against', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue', { name: 'margin_rate', mark: 'line' }],
			}).seriesConfig,
		).toEqual({ margin_rate: { type: 'line' } })
	})

	// @feature charts.series-type
	it('reads a mark the form wrote in the other case', () => {
		// Three releases of the Y Axis form wrote 'Line' and 'Bar'.
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue', { name: 'margin_rate', mark: 'Line' }],
			}).seriesConfig,
		).toEqual({ margin_rate: { type: 'line' } })
	})

	// @feature charts.line-area
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

	// @feature charts.series-type charts.line-data-points
	it('lets a Series override what the whole axis asked for', () => {
		expect(
			propsOf({
				type: 'Line',
				dimension: 'region',
				measures: [
					{ name: 'revenue', color: '#ff0000', dataLabels: true, dataPoints: true },
				],
			}).seriesConfig,
		).toEqual({
			revenue: { color: '#ff0000', showDataLabels: true, showDataPoints: true },
		})
	})

	// @feature charts.series-data-labels
	it('labels every series when the axis asks, and one series can ask alone', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue', 'target'],
				dataLabels: true,
			}).seriesConfig,
		).toEqual({ revenue: { showDataLabels: true }, target: { showDataLabels: true } })

		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				measures: ['revenue', { name: 'target', dataLabels: true }],
			}).seriesConfig,
		).toEqual({ target: { showDataLabels: true } })
	})

	// @feature charts.line-smooth
	it('curves a line when the axis asks, and one series can ask alone', () => {
		expect(
			propsOf({
				type: 'Line',
				dimension: 'region',
				measures: ['revenue', 'target'],
				smooth: true,
			}).seriesConfig,
		).toEqual({ revenue: { smooth: true }, target: { smooth: true } })

		expect(
			propsOf({
				type: 'Line',
				dimension: 'region',
				measures: ['revenue', { name: 'target', smooth: true }],
			}).seriesConfig,
		).toEqual({ target: { smooth: true } })
	})

	// @feature charts.split-by
	it('leaves the columns of a split uncolored, which the one color would flatten', () => {
		// A split hands one Series every column it produced, and the form writes
		// one color. Painting it on each of them draws the whole split in a single
		// shade, so the palette colors them instead. Everything else the Series
		// says is true of all its columns and still reaches them.
		const props = propsOf({
			type: 'Bar',
			dimension: 'order_date',
			measures: [{ name: 'revenue', color: '#ff0000', dataLabels: true }],
			splitBy: { dimension: 'region', into: ['North', 'South'] },
		})
		expect(props.seriesConfig).toEqual({
			North: { showDataLabels: true },
			South: { showDataLabels: true },
		})
	})

	// @feature charts.bar-overlap
	it('sends bars standing in front of each other through `echartOptions`', () => {
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
	// @feature charts.series-align
	it('measures a Series aligned right against an axis of its own', () => {
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue', { name: 'margin_rate', mark: 'line', axis: 'right' }],
		})
		expect(props.seriesConfig.margin_rate.axis).toBe('y2')
	})

	// @feature charts.series-align
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

	// @feature charts.type-row
	it('says the same for a row chart, whose one value axis is v2’s concern', () => {
		// A row chart runs its value axis across the plot. A second one along the
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
	// @feature charts.axis-label
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
		).toMatchObject({ title: 'Revenue (₹)', min: 0, max: 500 })
	})

	// @feature charts.bar-normalize
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
		// would cut the plot off. What is left is the formatter, which every axis
		// carries.
		expect(Object.keys(props.yAxis)).toEqual(['format'])
	})

	// @feature charts.axis-min-max
	it('pins the value axis to the bounds the author set, and leaves it free otherwise', () => {
		const bounded = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue'],
			min: 0,
			max: 500,
		}).yAxis
		expect(bounded.min).toBe(0)
		expect(bounded.max).toBe(500)

		// A bound nobody set is no bound: echarts fits the axis to the data, and a
		// key holding `undefined` would pin it to nothing.
		const free = propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] }).yAxis
		expect(Object.keys(free)).toEqual(['format'])
	})

	// @feature charts.bar-stack
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

	// @feature charts.axis-min-max
	it('ignores a bound that is not a number', () => {
		// a cleared box saved '', which frappe-ui would pin the axis to
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue'],
			min: '' as any,
			max: '' as any,
		})
		expect(Object.keys(props.yAxis)).toEqual(['format'])
	})
})

describe('bars on both value axes', () => {
	// A series with no align draws on the left.
	// @feature charts.bar-stack charts.bar-normalize charts.series-align
	it('neither stack nor normalize, whatever the Chart saved', () => {
		const measures = ['revenue', { name: 'refunds', axis: 'right' as const }]
		expect(
			propsOf({ type: 'Bar', dimension: 'region', measures, stacked: true }).stacked,
		).toBeUndefined()
		expect(
			propsOf({ type: 'Bar', dimension: 'region', measures, stacked: true, normalized: true })
				.stacked,
		).toBeUndefined()
	})

	// @feature charts.bar-overlap
	it('do not overlap', () => {
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue', { name: 'refunds', axis: 'right' }],
			overlap: true,
		})
		expect(props.seriesConfig?.revenue?.echartOptions).toBeUndefined()
	})

	// A line never stacks, so the bars on the left stack alone on their own scale.
	// @feature charts.bar-stack
	it('are not what a line on the right makes, so the bars still stack', () => {
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue', 'refunds', { name: 'sla', mark: 'Line', axis: 'right' }],
			stacked: true,
		})
		expect(props.stacked).toBe(true)
	})

	// A Row draws horizontally, and frappe-ui gives it no second value axis.
	// @feature charts.bar-stack
	it('never happen on a Row, so it keeps stacking', () => {
		const props = propsOf({
			type: 'Row',
			dimension: 'region',
			measures: ['revenue', { name: 'refunds', axis: 'right' }],
			stacked: true,
		})
		expect(props.stacked).toBe(true)
	})
})

describe('reference lines', () => {
	// @feature charts.reference-lines
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

	// @feature charts.reference-lines
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

	// @feature charts.reference-lines
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

	// @feature charts.reference-lines
	it('adds nothing at all when the Chart has none', () => {
		expect(
			propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] }).referenceLines,
		).toBeUndefined()
	})
})

describe('a reference line at an aggregate', () => {
	// Three readings with no aggregate in common, so every case below names one
	// number and one number only.
	const readings = { revenue: [10, 20, 60] }
	const spec = (line: ReferenceLine): AxisChartSpec => ({
		type: 'Bar',
		dimension: 'region',
		categories: ['North', 'South', 'East'],
		measures: ['revenue'],
		readings,
		referenceLines: [line],
	})
	const valueOf = (line: ReferenceLine) => propsOf(spec(line)).referenceLines?.[0]?.value

	// @feature charts.reference-lines
	it('reads the average of what the Chart draws', () => {
		expect(valueOf({ aggregate: 'average', measure_name: 'revenue' })).toBe(30)
	})

	// @feature charts.reference-lines
	it('reads the median, min, max and sum off the same numbers', () => {
		expect(valueOf({ aggregate: 'median', measure_name: 'revenue' })).toBe(20)
		expect(valueOf({ aggregate: 'min', measure_name: 'revenue' })).toBe(10)
		expect(valueOf({ aggregate: 'max', measure_name: 'revenue' })).toBe(60)
		expect(valueOf({ aggregate: 'sum', measure_name: 'revenue' })).toBe(90)
	})

	// @feature charts.reference-lines
	it('averages the two middle readings when there is no middle one', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				categories: ['North', 'South'],
				measures: ['revenue'],
				readings: { revenue: [10, 30] },
				referenceLines: [{ aggregate: 'median', measure_name: 'revenue' }],
			}).referenceLines,
		).toEqual([{ value: 20, axis: 'y', label: 'Median revenue: 20' }])
	})

	// @feature charts.reference-lines
	it('reads every column a split named after its own values', () => {
		// One Measure, four cells. The rule sits at the average cell, which is what
		// a reader compares each bar against.
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				categories: ['North', 'South'],
				measures: ['revenue'],
				splitBy: { dimension: 'channel', into: ['Retail', 'Online'] },
				readings: { Retail: [10, 20], Online: [30, 40] },
				referenceLines: [{ aggregate: 'average', measure_name: 'revenue' }],
			}).referenceLines,
		).toEqual([{ value: 25, axis: 'y', label: 'Avg revenue: 25' }])
	})

	// @feature charts.reference-lines
	it('reads its own Measure and no other', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				categories: ['North', 'South'],
				measures: ['revenue', 'refunds'],
				readings: { revenue: [10, 20], refunds: [100, 200] },
				referenceLines: [{ aggregate: 'average', measure_name: 'revenue' }],
			}).referenceLines?.[0]?.value,
		).toBe(15)
	})

	// @feature charts.reference-lines
	it('skips a cell it cannot read rather than counting it as zero', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				categories: ['North', 'South', 'East'],
				measures: ['revenue'],
				readings: { revenue: [10, null, 'n/a'] },
				referenceLines: [{ aggregate: 'average', measure_name: 'revenue' }],
			}).referenceLines?.[0]?.value,
		).toBe(10)
	})

	// @feature charts.reference-lines
	it('reads a right-aligned computed line against the second axis', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				categories: ['North', 'South'],
				measures: ['revenue', { name: 'margin_rate', axis: 'right' }],
				readings: { margin_rate: [4, 8] },
				referenceLines: [{ aggregate: 'max', measure_name: 'margin_rate', align: 'Right' }],
			}).referenceLines,
		).toEqual([{ value: 8, axis: 'y2', label: 'Max margin_rate: 8' }])
	})

	// @feature charts.reference-lines
	it("labels a right-aligned line in the second axis's own unit", () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				categories: ['North', 'South'],
				measures: ['revenue', { name: 'margin_rate', axis: 'right', format: 'percent' }],
				readings: { margin_rate: [0.04, 0.08] },
				referenceLines: [{ aggregate: 'max', measure_name: 'margin_rate', align: 'Right' }],
			}).referenceLines,
		).toEqual([{ value: 0.08, axis: 'y2', label: 'Max margin_rate: 8%' }])
	})

	// @feature charts.reference-lines
	it('names itself after the aggregate it read, printed as the axis prints it', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				categories: ['North', 'South'],
				measures: ['revenue'],
				readings: { revenue: [1000000, 1400000] },
				referenceLines: [{ aggregate: 'average', measure_name: 'revenue' }],
			}).referenceLines,
		).toEqual([{ value: 1200000, axis: 'y', label: 'Avg revenue: 1,200,000' }])
	})

	// @feature charts.reference-lines
	it('prints the label the author typed instead of its own', () => {
		expect(
			propsOf(spec({ aggregate: 'average', measure_name: 'revenue', label: 'Target' }))
				?.referenceLines,
		).toEqual([{ value: 30, axis: 'y', label: 'Target' }])
	})

	// @feature charts.reference-lines
	it('drops a line whose Measure the Chart does not draw', () => {
		expect(valueOf({ aggregate: 'average', measure_name: 'target' })).toBeUndefined()
	})

	// @feature charts.reference-lines
	it('drops a line with a Measure but no aggregate, and an aggregate but no Measure', () => {
		expect(valueOf({ measure_name: 'revenue' })).toBeUndefined()
		expect(valueOf({ aggregate: 'average' })).toBeUndefined()
	})

	// @feature charts.reference-lines
	it('drops a line whose Measure came back with nothing numeric', () => {
		expect(
			propsOf({
				type: 'Bar',
				dimension: 'region',
				categories: ['North', 'South'],
				measures: ['revenue'],
				readings: { revenue: [null, ''] },
				referenceLines: [{ aggregate: 'average', measure_name: 'revenue' }],
			}).referenceLines,
		).toBeUndefined()
	})
})

describe('a Measure that only reaches the tooltip', () => {
	const spec: AxisChartSpec = {
		type: 'Bar',
		dimension: 'region',
		measures: ['conversion_rate'],
		tooltipMeasures: ['order_count'],
	}

	// @feature charts.tooltip-measures
	it('is handed over as a tooltip column, not as a series', () => {
		const props = propsOf(spec)
		expect(props.y).toEqual(['conversion_rate'])
		expect(props.tooltipColumns).toHaveLength(1)
		expect(props.tooltipColumns[0].name).toBe('order_count')
	})

	// The result carries it as one more numeric column, so without the config
	// saying otherwise it would be read as a series and drawn.
	// @feature charts.tooltip-measures
	it('is taken out of the columns the chart draws', () => {
		const input = axisChart(spec)
		expect(input.result.columns.map((column) => column.name)).toContain('order_count')
		expect(adaptChart(input)!.props.y).not.toContain('order_count')
	})

	// The chart labels a column the way it labels a series it draws, so naming
	// one here would make the same Measure read two ways.
	// @feature charts.tooltip-measures
	it('names itself the way a drawn Measure does', () => {
		expect(propsOf(spec).tooltipColumns[0].label).toBeUndefined()
	})

	// @feature charts.tooltip-measures
	it('prints through the Chart number format, the way a series value does', () => {
		const input = axisChart(spec)
		// The Chart-level default every value inherits.
		;(input.config as any).number_format = { prefix: '#', decimals: 0 }
		const format = adaptChart(input)!.props.tooltipColumns[0].format
		expect(format(1840)).toBe('#1,840')
	})

	// @feature charts.tooltip-measures
	it('prints a text attribute as it stands', () => {
		const format = propsOf(spec).tooltipColumns[0].format
		expect(format('Outerwear')).toBe('Outerwear')
	})

	// A split turns every Measure into one column per split value, which is a
	// value per mark. The server leaves tooltip Measures out of that pivot, so
	// there is no column for one to arrive on.
	// @feature charts.tooltip-measures
	it('is dropped under a split', () => {
		const props = propsOf({
			...spec,
			splitBy: { dimension: 'department', into: ['Men', 'Women'] },
		})
		expect(props.tooltipColumns).toBeUndefined()
		expect(props.y).toEqual(['Men', 'Women'])
	})

	// A tooltip Measure is not drawn, but it is measured. A target on the tooltip
	// is the kind of number a rule reads, so a line has to be able to name one.
	// @feature charts.tooltip-measures
	it('can still back a computed reference line', () => {
		const props = propsOf({
			...spec,
			readings: { order_count: [10, 30] },
			referenceLines: [{ aggregate: 'average', measure_name: 'order_count' }],
		})
		expect(props.referenceLines).toEqual([
			{ value: 20, axis: 'y', label: 'Avg order_count: 20' },
		])
	})

	// @feature charts.tooltip-measures
	it('says nothing when the Chart names none', () => {
		const props = propsOf({ type: 'Bar', dimension: 'region', measures: ['revenue'] })
		expect(props.tooltipColumns).toBeUndefined()
	})

	// Two Measures under one name is one column. Drawing wins: the chart would
	// otherwise lose a series to the tooltip.
	// @feature charts.tooltip-measures
	it('yields a name the chart already draws', () => {
		const props = propsOf({
			type: 'Bar',
			dimension: 'region',
			measures: ['revenue'],
			tooltipMeasures: ['revenue'],
		})
		expect(props.y).toEqual(['revenue'])
		expect(props.tooltipColumns).toBeUndefined()
	})
})

describe('drilling into a point', () => {
	// @feature charts.drill-segment
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
				name: 'revenue',
				value: row.revenue,
				row,
			}),
		).toEqual({ column: 'revenue', row })
	})

	// The column a split segment names is a pivoted one, which only the result
	// carries — a drill that named the Measure would fail to find it there.
	// @feature charts.drill-segment
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
				name: series,
				value: row[series],
				row,
			})
			expect(target).toEqual({ column: series, row })
			// what the card then looks the column up by
			expect(input.result.columns.map((c) => c.name)).toContain(target!.column)
		}
	})
})
