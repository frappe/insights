import { describe, expect, it } from 'vitest'
import {
	dataSelection,
	ensureConfigSlots,
	getGranularity,
	handleOldHideFromChart,
	handleOldNumberShapes,
	handleOldSeriesTypes,
	moveNumberReadingOptions,
	normalizeChartConfig,
	removeNumberReading,
	resetChartConfig,
	setDimensionNames,
} from './helpers'

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
	// @feature charts.tooltip-measures
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

	// @feature charts.tooltip-measures
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

	// @feature charts.tooltip-measures
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

	// @feature charts.tooltip-measures
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
	// @feature charts.tooltip-measures
	it('is left alone when no series is hidden', () => {
		const before = config([{ measure: measure('revenue') }])
		expect(handleOldHideFromChart(before).tooltip).toBeUndefined()
	})

	// Moving every series would leave the adapter no value column to plot, and it
	// draws nothing at all rather than an empty plot.
	// @feature charts.tooltip-measures
	it('is left alone when every series is hidden', () => {
		const before = config([
			{ measure: measure('revenue'), hide_from_chart: true },
			{ measure: measure('orders'), hide_from_chart: true },
		])
		const after = handleOldHideFromChart(before)
		expect(after.tooltip).toBeUndefined()
		expect(after.y_axis.series).toHaveLength(2)
	})

	// @feature charts.tooltip-measures
	it('leaves a chart type that carries no series untouched', () => {
		const before = { label_column: {}, value_column: {} } as any
		expect(handleOldHideFromChart(before)).toBe(before)
	})
})

describe('a Dimension saved before it carried its own name', () => {
	// Every slot, so a reader never falls back to `column_name` for the ones the
	// normalizer forgot.
	// @feature charts.dimension-label
	it('is named after its column, in every slot a Dimension stands in', () => {
		const before = {
			x_axis: { dimension: { column_name: 'region' } },
			split_by: { dimension: { column_name: 'channel' } },
			date_column: { column_name: 'posting_date' },
			label_column: { column_name: 'item' },
			source_column: { column_name: 'from' },
			target_column: { column_name: 'to' },
			x_column: { column_name: 'day' },
			y_column: { column_name: 'hour' },
			dimension: { column_name: 'customer' },
			quadrant_column: { column_name: 'territory' },
			location_column: { column_name: 'state' },
			rows: [{ column_name: 'company' }],
			columns: [{ column_name: 'month' }],
		} as any

		const after = setDimensionNames(before)

		expect(after.x_axis.dimension.dimension_name).toBe('region')
		expect(after.split_by.dimension.dimension_name).toBe('channel')
		expect(after.date_column.dimension_name).toBe('posting_date')
		expect(after.label_column.dimension_name).toBe('item')
		expect(after.source_column.dimension_name).toBe('from')
		expect(after.target_column.dimension_name).toBe('to')
		expect(after.x_column.dimension_name).toBe('day')
		expect(after.y_column.dimension_name).toBe('hour')
		expect(after.dimension.dimension_name).toBe('customer')
		expect(after.quadrant_column.dimension_name).toBe('territory')
		expect(after.location_column.dimension_name).toBe('state')
		expect(after.rows[0].dimension_name).toBe('company')
		expect(after.columns[0].dimension_name).toBe('month')
	})

	// @feature charts.dimension-label
	it('keeps the name it already carries', () => {
		const after = setDimensionNames({ x_column: { column_name: 'day', dimension_name: 'Day' } })
		expect(after.x_column.dimension_name).toBe('Day')
	})
})

describe('getGranularity', () => {
	// @feature charts.dimension-grain
	it('reads the grain off a slot only the newer chart types carry', () => {
		const config = {
			x_column: { dimension_name: 'posting_date', granularity: 'month' },
		} as any
		expect(getGranularity('posting_date', config)).toBe('month')
	})

	// @feature charts.dimension-grain
	it('reads the grain off an axis', () => {
		const config = {
			x_axis: { dimension: { dimension_name: 'posting_date', granularity: 'week' } },
		} as any
		expect(getGranularity('posting_date', config)).toBe('week')
	})

	// @feature charts.dimension-grain
	it('answers with nothing for a column no slot holds', () => {
		expect(getGranularity('posting_date', { rows: [] } as any)).toBeUndefined()
	})
})

describe('a Bar saved with bars on both axes', () => {
	// The adapter ignores the flags while the layout holds. Writing them back on
	// load would lose them for good the next time the rule is corrected.
	// @feature charts.bar-stack
	it('keeps the flags it was saved with', () => {
		const after = normalizeChartConfig(
			{
				y_axis: {
					stack: true,
					overlap: true,
					normalize: true,
					series: [
						{ measure: measure('revenue') },
						{ measure: measure('refunds'), align: 'Right' },
					],
				},
			},
			'Bar',
		)
		expect(after.y_axis).toMatchObject({ stack: true, overlap: true, normalize: true })
	})
})

describe('a y axis saved with a cleared bound', () => {
	// @feature charts.axis-min-max
	it('drops the empty bound and keeps the one the author typed', () => {
		const before = config([{ measure: measure('revenue') }])
		before.y_axis.min = '5'
		before.y_axis.max = ''
		const after = normalizeChartConfig(before, 'Bar')
		expect(after.y_axis.min).toBe(5)
		expect('max' in after.y_axis).toBe(false)
	})
})

describe('the stack default on a Bar', () => {
	// @feature charts.bar-stack
	it('is written for a chart that names no series yet', () => {
		const after = ensureConfigSlots({}, 'Bar')
		expect(after.y_axis.stack).toBe(true)
	})

	// @feature charts.bar-stack
	it('is left off a saved chart that was drawn grouped', () => {
		const after = ensureConfigSlots(config([{ measure: measure('revenue') }]), 'Bar')
		expect(after.y_axis.stack).toBeUndefined()
	})

	// @feature charts.bar-stack
	it('keeps what the author chose', () => {
		const before = config([{ measure: measure('revenue') }])
		before.y_axis.stack = true
		expect(ensureConfigSlots(before, 'Bar').y_axis.stack).toBe(true)
	})
})

describe('a series whose type the form wrote in the other case', () => {
	// @feature charts.series-type
	it('is folded to the case the renderer reads', () => {
		const before = config([
			{ measure: measure('revenue') },
			{ measure: measure('margin_rate'), type: 'Line' },
		])
		expect(handleOldSeriesTypes(before).y_axis.series[1].type).toBe('line')
	})

	// @feature charts.series-type
	it('leaves a chart that names no series alone', () => {
		expect(handleOldSeriesTypes({} as any)).toEqual({})
	})
})

// The server reads these three shapes on every read path. The renderer reads the
// stored config itself, so it has to read them too: a config can still arrive in
// an old shape after the patch has run — an import, or another app's template.
describe('a Number card saved in an older shape', () => {
	const numberCard = (readings: string[], rest: any = {}) => ({
		number_columns: readings.map((name) => ({ measure_name: name, column_name: name })),
		...rest,
	})

	// @feature upgrade.number-older-shapes
	it('reads the chart-level flag as one previous comparison per reading', () => {
		const config = handleOldNumberShapes(
			numberCard(['revenue', 'profit'], { comparison: true }),
		)

		expect(config.comparison).toBeUndefined()
		expect(config.number_column_options.map((o: any) => o.comparison)).toEqual([
			{ source: 'previous' },
			{ source: 'previous' },
		])
	})

	// @feature upgrade.number-older-shapes
	it('reads a reference list as the movement and the target', () => {
		const config = handleOldNumberShapes(
			numberCard(['revenue'], {
				number_column_options: [
					{
						references: [
							{ source: 'previous', label: 'vs last month' },
							{ source: 'constant', value: 400, show: 'attainment' },
						],
					},
				],
			}),
		)

		const beside = config.number_column_options[0]
		expect(beside.references).toBeUndefined()
		expect(beside.comparison).toEqual({
			source: 'previous',
			show: 'change',
			label: 'vs last month',
		})
		expect(beside.target).toEqual({ value: 400 })
	})

	// @feature upgrade.number-older-shapes
	it('raises a granularity on the date column into the period', () => {
		const config = handleOldNumberShapes(
			numberCard(['revenue'], {
				date_column: { column_name: 'posting_date', granularity: 'month' },
			}),
		)

		expect(config.window).toEqual({ grain: 'month' })
		expect(config.date_column.granularity).toBeUndefined()
	})

	// @feature upgrade.number-older-shapes
	it('reads a shifted window comparison as the question it asked', () => {
		const config = handleOldNumberShapes(
			numberCard(['revenue'], {
				number_column_options: [
					{ comparison: { source: 'window', shift: { unit: 'year', count: -1 } } },
				],
			}),
		)

		expect(config.number_column_options[0].comparison).toEqual({ source: 'last year' })
	})

	// @feature upgrade.number-older-shapes
	it('leaves a reading that names its own alone', () => {
		const named = { source: 'constant', value: 10 }
		const config = handleOldNumberShapes(
			numberCard(['revenue', 'profit'], {
				comparison: true,
				number_column_options: [{ comparison: named }, {}],
			}),
		)

		expect(config.number_column_options[0].comparison).toEqual(named)
		expect(config.number_column_options[1].comparison).toEqual({ source: 'previous' })
	})
})

describe('the half of a config that decides which rows come back', () => {
	const bar = (series: any[], extra: any = {}) => ({
		x_axis: { dimension: { column_name: 'region', dimension_name: 'region' } },
		y_axis: { series },
		limit: 100,
		...extra,
	})

	// @feature charts.series-color
	it('is unmoved by a series color', () => {
		const before = dataSelection(bar([{ measure: measure('revenue') }]))
		const after = dataSelection(bar([{ measure: measure('revenue'), color: ['#fff'] }]))
		expect(after).toEqual(before)
	})

	// @feature charts.style-change-no-rerun
	it('is unmoved by a data label, an axis label or a number format', () => {
		const before = dataSelection(bar([{ measure: measure('revenue') }]))
		const after = dataSelection(
			bar([{ measure: measure('revenue'), show_data_labels: true }], {
				number_format: { shorten: true },
				y_axis_label: 'Revenue',
			}),
		)
		expect(after).toEqual(before)
	})

	// @feature charts.style-change-no-rerun
	it('moves when a measure changes', () => {
		const before = dataSelection(bar([{ measure: measure('revenue') }]))
		const after = dataSelection(bar([{ measure: measure('margin') }]))
		expect(after).not.toEqual(before)
	})

	// @feature charts.limit
	it('moves when the row cap changes', () => {
		const before = dataSelection(bar([{ measure: measure('revenue') }]))
		const after = dataSelection(bar([{ measure: measure('revenue') }], { limit: 50 }))
		expect(after).not.toEqual(before)
	})

	// @feature charts.style-change-no-rerun
	it('reads a tooltip measure, which is fetched and not drawn', () => {
		const before = dataSelection(bar([{ measure: measure('revenue') }]))
		const after = dataSelection(
			bar([{ measure: measure('revenue') }], { tooltip: { measures: [measure('count')] } }),
		)
		expect(after).not.toEqual(before)
	})

	// @feature charts.style-change-no-rerun
	it("moves when a reading's comparison changes, which fetches its own rows", () => {
		const card = (comparison: any) => ({
			number_columns: [measure('revenue')],
			number_column_options: [{ comparison }],
		})
		expect(dataSelection(card({ source: 'previous' }))).not.toEqual(
			dataSelection(card({ source: 'last year' })),
		)
	})
})

// Taking the options back is not taking the chart back: the query the card runs
// is `filters` and `limit`, and a reset that dropped them would send the author
// back to a reading of every row.

describe('a chart whose author took the options back', () => {
	// @feature charts.reset-options
	it('a reset keeps the filters and the limit and empties every slot', () => {
		const filters = {
			logical_operator: 'And',
			filters: [
				{
					column: { column_name: 'region' },
					operator: '=',
					value: 'North',
				},
			],
		}

		const reset = resetChartConfig(
			{
				x_axis: { dimension: { column_name: 'region', dimension_name: 'region' } },
				y_axis: {
					series: [{ measure: measure('revenue') }, { measure: measure('margin') }],
					stack: true,
				},
				order_by: [{ column: { column_name: 'revenue' }, direction: 'desc' }],
				filters,
				limit: 10,
			},
			'Bar',
		)

		expect(reset).toEqual({
			x_axis: { dimension: {} },
			y_axis: { series: [{ measure: {} }], stack: true },
			order_by: [],
			filters,
			limit: 10,
		})
	})
})

// A Number card's readings and their options are paired by position, and this
// is the pairing's only writer. A reading removed or dragged without its
// options left the readings after it reading the target, the comparison and the
// color of the reading that used to be in their place — and a target and a
// comparison are what the server is asked to resolve.

describe("a reading's options follow the reading", () => {
	const card = () => ({
		number_columns: [measure('a'), measure('b'), measure('c')],
		number_column_options: [{ target: 'ta' }, { target: 'tb' }, { target: 'tc' }],
	})

	// @feature charts.number-readings
	it("drops the removed reading's options, not the next one's", () => {
		const config = card()
		removeNumberReading(config, 1)
		expect(config.number_columns.map((m: any) => m.measure_name)).toEqual(['a', 'c'])
		expect(config.number_column_options).toEqual([{ target: 'ta' }, { target: 'tc' }])
	})

	// @feature charts.number-readings
	it("moves the dragged reading's options with it", () => {
		const config = card()
		// what `DraggableList` does to the readings before it reports the move
		config.number_columns.splice(0, 0, config.number_columns.splice(2, 1)[0])
		moveNumberReadingOptions(config, 2, 0)
		expect(config.number_columns.map((m: any) => m.measure_name)).toEqual(['c', 'a', 'b'])
		expect(config.number_column_options).toEqual([
			{ target: 'tc' },
			{ target: 'ta' },
			{ target: 'tb' },
		])
	})

	// @feature charts.number-readings
	it('pads a short options array first, so the pairing cannot slide', () => {
		// an option is written only where an author set one
		const config = {
			number_columns: [measure('a'), measure('b'), measure('c')],
			number_column_options: [{ target: 'ta' }],
		} as any
		removeNumberReading(config, 0)
		expect(config.number_columns.map((m: any) => m.measure_name)).toEqual(['b', 'c'])
		expect(config.number_column_options).toEqual([{}, {}])
	})

	// @feature charts.number-readings
	it('writes an options array where the card has none', () => {
		const config = { number_columns: [measure('a'), measure('b')] } as any
		moveNumberReadingOptions(config, 1, 0)
		expect(config.number_column_options).toEqual([{}, {}])
	})
})

describe('a Number reading saved without an id', () => {
	// @feature dashboard.number-cell-per-reading
	it('takes its Measure name, the name a cell written before ids named it by', () => {
		const after = ensureConfigSlots({ number_columns: [measure('Revenue')] }, 'Number')
		expect(after.number_columns[0].id).toBe('Revenue')
	})

	// @feature dashboard.number-cell-per-reading
	it('keeps the id it was saved with when its Measure is renamed', () => {
		const after = ensureConfigSlots(
			{ number_columns: [{ ...measure('Margin'), id: 'Profit' }] },
			'Number',
		)
		expect(after.number_columns[0].id).toBe('Profit')
	})
})
