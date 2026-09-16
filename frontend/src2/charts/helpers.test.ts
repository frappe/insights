import { describe, expect, it } from 'vitest'
import {
	dataSelection,
	ensureConfigSlots,
	getGranularity,
	moveNumberReadingOptions,
	normalizeChartConfig,
	removeNumberReading,
	resetChartConfig,
	setDimensionNames,
} from './helpers'

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

// Every older shape a stored config still carries, anonymized from the configs
// on insights.frappe.io. `insights.patches.normalize_chart_configs` rewrites
// them once. The load path's job here is to leave them as they are.
const olderShapes: { shape: string; chart_type: string; config: any }[] = [
	{
		shape: 'an axis that was the dimension itself',
		chart_type: 'Line',
		config: {
			x_axis: { column_name: 'posting_date', data_type: 'Date', granularity: 'month' },
			split_by: { column_name: 'region', data_type: 'String' },
			y_axis: { series: [{ measure: measure('revenue') }] },
		},
	},
	{
		shape: 'a value axis that was the list of measures on it',
		chart_type: 'Bar',
		config: { y_axis: [measure('revenue')] },
	},
	{
		shape: 'a series hidden from the chart, and one marked in the other case',
		chart_type: 'Bar',
		config: {
			y_axis: {
				series: [
					{ measure: measure('revenue'), type: 'Bar' },
					{ measure: measure('margin'), type: 'Line', hide_from_chart: true },
				],
				min: '0',
				max: '',
			},
		},
	},
	{
		shape: 'a reference line saved before it carried an id',
		chart_type: 'Line',
		config: {
			y_axis: {
				series: [{ measure: measure('revenue') }],
				reference_lines: [{ axis: 'y', value: 500, statistic: 'average' }],
			},
		},
	},
	{
		shape: 'a picked option written where a dimension is declared',
		chart_type: 'Table',
		config: {
			limit: '1000',
			rows: [
				{ column_name: 'region', data_type: 'String', label: 'region', value: 'region' },
			],
			columns: [],
			values: [measure('revenue')],
			max_column_values: '',
		},
	},
	{
		shape: 'a card that said which way is up for every reading',
		chart_type: 'Number',
		config: {
			number_columns: [measure('revenue'), measure('churn')],
			number_column_options: [],
			negative_is_better: true,
			date_column: { column_name: 'posting_date', granularity: 'month' },
		},
	},
]

/** Every value the config states, by the path that states it. */
function stated(node: any, path = ''): Record<string, any> {
	if (Array.isArray(node)) {
		return Object.assign(
			{ [`${path}.length`]: node.length },
			...node.map((i, n) => stated(i, `${path}[${n}]`)),
		)
	}
	if (node && typeof node === 'object') {
		return Object.assign({}, ...Object.entries(node).map(([k, v]) => stated(v, `${path}.${k}`)))
	}
	return { [path]: node }
}

describe('a config saved in an older shape', () => {
	for (const { shape, chart_type, config: older } of olderShapes) {
		// @feature upgrade.chart-config-older-shapes
		it(`keeps every value ${shape} states`, () => {
			const before = stated(older)
			const after = stated(normalizeChartConfig(structuredClone(older), chart_type))
			for (const [path, value] of Object.entries(before)) {
				expect({ path, value: after[path] }).toEqual({ path, value })
			}
		})

		// @feature upgrade.chart-config-older-shapes
		it(`reads ${shape} the same way twice`, () => {
			const once = normalizeChartConfig(structuredClone(older), chart_type)
			expect(normalizeChartConfig(structuredClone(once), chart_type)).toEqual(once)
		})
	}
})
