import { describe, expect, it } from 'vitest'
import { EMPTY_RESULT } from '../../query/helpers'
import { ROW_HEIGHT } from '../../dashboard/grid_placement'
import type { NumberChartConfig } from '../../types/chart.types'
import { numberChart, type NumberChartSpec } from './fixtures'
import { defaultComparisonLabel, numberCardRows } from './number'
import { adaptChart, drawsOwnCards } from './index'
import NumberCards from './NumberCards.vue'

function adapt(spec: NumberChartSpec) {
	const filler = adaptChart(numberChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const cardsOf = (spec: NumberChartSpec) => adapt(spec).props.cards

/** A result column read as a measure, the way a target column is named. */
const measureNamed = (name: string) => ({
	column_name: name,
	data_type: 'Decimal' as const,
	aggregation: 'sum' as const,
	measure_name: name,
})

const monthly = { name: 'created_at', type: 'Datetime', granularity: 'month' } as const

const revenue = { name: 'Revenue', readings: [12300] }

describe('a Number Chart with several values', () => {
	it('previews every reading, one card behind each of them', () => {
		// What the workbook editor draws: the chart states three readings, so all
		// three stand side by side. It draws no chrome — the card around it is the
		// one every other chart type gets.
		const { component, props } = adapt({
			values: [
				{ name: 'Revenue', readings: [100] },
				{ name: 'Profit', readings: [40] },
				{ name: 'Items', readings: [7] },
			],
		})

		expect(component).toBe(NumberCards)
		expect(props.cards.map((card: any) => card.title)).toEqual(['Revenue', 'Profit', 'Items'])
		expect(props.cards.map((card: any) => card.value)).toEqual([100, 40, 7])
	})

	it('previews the cards at cell size when no cell names a reading', () => {
		// The editor has no cell to fill, so each card carries the height a cell
		// of its rows would give it, and the row is told to draw them that way.
		const { props } = adapt({ values: [{ name: 'Revenue', readings: [100] }] })
		expect(props.preview).toBe(true)
		expect(props.cards[0].height).toBe(4 * 22 - 16)

		const cell = adapt({ values: [{ name: 'Revenue', readings: [100] }], column: 'Revenue' })
		expect(cell.props.preview).toBe(false)
	})

	it('draws the cards itself, so the chrome draws none around them', () => {
		expect(drawsOwnCards('Number')).toBe(true)
	})

	it('reads the newest row, which is the reading a KPI states', () => {
		expect(cardsOf({ values: [{ name: 'Revenue', readings: [100, 300] }] })[0].value).toBe(300)
	})

	it('leaves a value with no reading empty, rather than calling it zero', () => {
		expect(cardsOf({ values: [{ name: 'Revenue', readings: [null] }] })[0].value).toBeNull()
	})

	it('draws nothing until the Chart names a Measure', () => {
		expect(adaptChart(numberChart({ values: [] }))).toBeUndefined()
	})

	it('stands the grid up from the config alone, so the cards wear the states', () => {
		// The cards are this type's only surface: a chart still running, or one
		// that failed, is drawn on them and not on a chrome it does not have. So
		// the grid is built before a result, with a titled card and no reading.
		const filler = adaptChart({
			...numberChart({ values: [{ name: 'Revenue', readings: [100] }] }),
			result: { ...EMPTY_RESULT },
		})

		expect(filler?.props.cards.map((card: any) => card.title)).toEqual(['Revenue'])
		expect(filler?.props.cards[0].value).toBeNull()
		// Nothing to drill into: no row stands behind the reading.
		expect(filler?.drillDown).toBeUndefined()
	})
})

describe('how a reading is printed', () => {
	it('takes the units and the rounding each value set for itself', () => {
		const cards = cardsOf({
			values: [
				{ name: 'Revenue', readings: [12300], prefix: '$', decimal: 1, shorten: true },
				{ name: 'Items', readings: [7] },
			],
		})
		expect(cards[0]).toMatchObject({ prefix: '$', precision: 1, compact: true })
		expect(cards[1].prefix).toBeUndefined()
		expect(cards[1].compact).toBeUndefined()
	})

	it('falls back to what the Chart set for every value', () => {
		const cards = cardsOf({
			values: [
				{ name: 'Revenue', readings: [12300] },
				{ name: 'Items', readings: [7], decimal: 0 },
			],
			decimal: 2,
			suffix: ' sold',
		})
		expect(cards[0]).toMatchObject({ precision: 2, suffix: ' sold' })
		expect(cards[1].precision).toBe(0)
	})

	it('prints a value in the ink it was given, and only that value', () => {
		// One color for one reading: it is the ink of the number, not a restyle of
		// the card it stands in.
		const cards = cardsOf({
			values: [
				{ name: 'Revenue', readings: [100], color: '#2490EF' },
				{ name: 'Items', readings: [7] },
			],
		})
		expect(cards[0].color).toBe('#2490EF')
		expect(cards[1].color).toBeUndefined()
	})

	it('scales a Measure that holds a fraction and states the unit', () => {
		// v2 prints a number. What the number means stays the caller's.
		const card = cardsOf({ values: [{ name: 'Margin', readings: [0.42], percent: true }] })[0]
		expect(card.value).toBe(42)
		expect(card.suffix).toBe('%')
	})
})

describe('the target', () => {
	it('hands the card the number itself, not a percentage of it reached', () => {
		// The card prints `$300 / $400` on the value line, in the units the value
		// is already formatted in, so the fraction states the attainment.
		const card = cardsOf({
			values: [{ name: 'Revenue', readings: [300], prefix: '$', targetValue: 400 }],
		})[0]
		expect(card.target).toBe(400)
		// A target is not a movement, so it says nothing in the delta row.
		expect(card.delta).toBeUndefined()
		expect(card.deltaCaption).toBeUndefined()
	})

	it('reads a target column off the same row the reading came from', () => {
		// A target is the target for the period on the card, not for the series.
		const card = cardsOf({
			values: [
				{ name: 'Revenue', readings: [100, 300], target: [500, 400], targetColumn: true },
			],
		})[0]
		expect(card.target).toBe(400)
	})

	it('scales a target the way it scales the fraction it is measured against', () => {
		const card = cardsOf({
			values: [{ name: 'Margin', readings: [0.42], percent: true, targetValue: 0.5 }],
		})[0]
		expect(card.target).toBe(50)
	})

	it('names none when the value aims at nothing, or at a column with no number', () => {
		expect(
			cardsOf({ values: [{ name: 'Revenue', readings: [300] }] })[0].target,
		).toBeUndefined()
		expect(
			cardsOf({
				values: [{ name: 'Revenue', readings: [300], target: [null], targetColumn: true }],
			})[0].target,
		).toBeUndefined()
	})
})

describe('the comparison', () => {
	const previous: NumberChartSpec = {
		values: [{ name: 'Revenue', readings: [200, 300], comparison: { source: 'previous' } }],
		period: monthly,
	}

	it('derives the change from the reading before it, as a percentage', () => {
		// v2 takes a computed delta and prints it. The arithmetic is the caller's.
		const card = cardsOf(previous)[0]
		expect(card.delta).toBe(50)
		expect(card.deltaSuffix).toBe('%')
	})

	it('says what the change is measured against, at the grain it was grouped by', () => {
		expect(cardsOf(previous)[0].deltaCaption).toBe('vs previous month')
	})

	it('reads that grain off the period, so a migrated card keeps its caption', () => {
		// The grain moved onto the chart and the form deletes it from the
		// dimension. Reading the dimension would leave the delta row unworded.
		const migrated = {
			date_column: { column_name: 'created_at', data_type: 'Datetime' },
			window: { grain: 'month' },
		} as unknown as NumberChartConfig

		expect(defaultComparisonLabel({ source: 'previous' }, migrated)).toBe('vs previous month')
	})

	it('words a shifted window off the shift, so the card needs no caption typed', () => {
		// Derivation returns the shifted window as the row before the last one, so
		// the figure reads the way `previous` does. What it is called comes from
		// the shift, because the dimension is a window and carries no grain.
		const card = cardsOf({
			values: [
				{
					name: 'Revenue',
					readings: [200, 300],
					comparison: { source: 'window', shift: { unit: 'year', count: -1 } },
				},
			],
		})[0]
		expect(card.delta).toBe(50)
		expect(card.deltaCaption).toBe('vs same period last year')
	})

	it('measures against a fixed number, and calls it the target when unworded', () => {
		const card = cardsOf({
			values: [
				{
					name: 'Revenue',
					readings: [300],
					comparison: { source: 'constant', value: 250 },
				},
			],
		})[0]
		expect(card.delta).toBe(20)
		expect(card.deltaCaption).toBe('vs target')
	})

	it('measures against a column, read off the row the reading came from', () => {
		const card = cardsOf({
			values: [
				{
					name: 'Revenue',
					readings: [100, 300],
					target: [500, 400],
					comparison: { source: 'measure', measure: measureNamed('Revenue_target') },
				},
			],
		})[0]
		expect(card.delta).toBe(-25)
	})

	it("states the gap in the value's own units when asked for a difference", () => {
		// The gap is money, so it carries the money sign the reading carries.
		const card = cardsOf({
			values: [
				{
					name: 'Revenue',
					readings: [300],
					prefix: '$',
					comparison: { source: 'constant', value: 400, show: 'delta', label: 'vs plan' },
				},
			],
		})[0]
		expect(card.delta).toBe(-100)
		expect(card.deltaPrefix).toBe('$')
		expect(card.deltaSuffix).toBeUndefined()
		expect(card.deltaCaption).toBe('vs plan')
	})

	it('leaves the unit off the gap, because the value line already carries it', () => {
		// The card reads "67 days / 45 days": a third "days" on the delta row
		// says nothing and pushes the caption out of the card.
		const card = cardsOf({
			values: [
				{
					name: 'Days of Inventory',
					readings: [67],
					suffix: ' days',
					comparison: { source: 'constant', value: 97, show: 'delta', label: 'vs plan' },
				},
			],
		})[0]
		expect(card.suffix).toBe(' days')
		expect(card.delta).toBe(-30)
		expect(card.deltaSuffix).toBeUndefined()
	})

	it("prints a percent measure's gap in points, not percent", () => {
		// 42% against a 42.8% target is a gap of 0.8 points, not -0.8%.
		const card = cardsOf({
			values: [
				{
					name: 'Margin',
					readings: [0.42],
					percent: true,
					comparison: { source: 'constant', value: 0.428, show: 'delta' },
				},
			],
		})[0]
		expect(card.delta).toBeCloseTo(-0.8)
		expect(card.deltaSuffix).toBe(' pts')
	})

	it('signs the change the way the data moved, and leaves the coloring to v2', () => {
		// The card flips its colors for a metric where a fall is good news, so
		// flipping the number here as well would flip it back.
		const card = cardsOf({
			values: [
				{
					name: 'Churn',
					readings: [300, 200],
					negativeIsBetter: true,
					comparison: { source: 'previous' },
				},
			],
			period: monthly,
		})[0]
		expect(card.delta).toBeCloseTo(-33.33, 2)
		expect(card.negativeIsBetter).toBe(true)
	})

	it('states no change when there is nothing to measure one from', () => {
		expect(
			cardsOf({
				values: [{ name: 'Revenue', readings: [300], comparison: { source: 'previous' } }],
				period: monthly,
			})[0].delta,
		).toBeNull()
		// A change from zero has no percentage.
		expect(
			cardsOf({
				values: [
					{ name: 'Revenue', readings: [0, 300], comparison: { source: 'previous' } },
				],
				period: monthly,
			})[0].delta,
		).toBeNull()
	})

	it('draws no delta row when the comparison names no number to hold the reading against', () => {
		const card = cardsOf({
			values: [{ name: 'Revenue', readings: [300], comparison: { source: 'constant' } }],
		})[0]
		expect(card.delta).toBeUndefined()
		expect(card.deltaCaption).toBeUndefined()
	})

	it('states none at all on a value that compares nothing', () => {
		const card = cardsOf({ values: [{ name: 'Revenue', readings: [200, 300] }] })[0]
		expect(card.delta).toBeUndefined()
		expect(card.deltaCaption).toBeUndefined()
	})
})

describe('a card carrying both a target and a comparison', () => {
	it('aims at the one and moves against the other, each in its own line', () => {
		const card = cardsOf({
			values: [
				{
					name: 'Revenue',
					readings: [200, 300],
					targetValue: 400,
					comparison: { source: 'previous', label: 'vs last month' },
				},
			],
			period: monthly,
		})[0]
		expect(card.target).toBe(400)
		expect(card.delta).toBe(50)
		expect(card.deltaCaption).toBe('vs last month')
	})
})

describe('a chart saved before a value named its own target and comparison', () => {
	it('reads the old comparison flag as one previous-period comparison', () => {
		const card = cardsOf({
			values: [{ name: 'Revenue', readings: [200, 300] }],
			period: monthly,
			comparison: true,
		})[0]
		expect(card.delta).toBe(50)
		expect(card.deltaCaption).toBe('vs previous month')
	})

	it('still falls back to what the chart set for negative-is-better', () => {
		const card = cardsOf({
			values: [{ name: 'Churn', readings: [300, 200] }],
			period: monthly,
			comparison: true,
			negativeIsBetter: true,
		})[0]
		expect(card.negativeIsBetter).toBe(true)
	})

	it('reads a reference list as the movement it held and the target it aimed at', () => {
		// One release wrote both as references. A movement is the comparison; an
		// attainment was only ever a target worded as a percentage.
		const card = cardsOf({
			values: [
				{
					name: 'Revenue',
					readings: [200, 300],
					references: [
						{ source: 'previous', label: 'vs last month' },
						{ source: 'constant', value: 400, show: 'attainment', label: 'of target' },
					],
				},
			],
			period: monthly,
		})[0]
		expect(card.target).toBe(400)
		expect(card.delta).toBe(50)
		expect(card.deltaCaption).toBe('vs last month')
	})

	it('reads an attainment reference on a column as a target read off that column', () => {
		const card = cardsOf({
			values: [
				{
					name: 'Revenue',
					readings: [100, 300],
					target: [500, 400],
					references: [
						{
							source: 'measure',
							measure: measureNamed('Revenue_target'),
							show: 'attainment',
						},
					],
				},
			],
			period: monthly,
		})[0]
		expect(card.target).toBe(400)
		expect(card.delta).toBeUndefined()
	})

	it('takes the value at its word when it named its own references, including none', () => {
		const card = cardsOf({
			values: [{ name: 'Revenue', readings: [200, 300], references: [] }],
			period: monthly,
			comparison: true,
		})[0]
		expect(card.delta).toBeUndefined()
		expect(card.target).toBeUndefined()
	})
})

describe('the sparkline', () => {
	it('carries every reading, oldest first, and the color the Chart chose', () => {
		const card = cardsOf({
			values: [{ name: 'Items', readings: [7, 9, 8] }],
			period: monthly,
			sparkline: true,
			sparklineColor: '#2490EF',
		})[0]
		expect(card.sparkline).toEqual({ data: [7, 9, 8], color: '#2490EF' })
	})

	it('draws none without a Dimension to run the trend along', () => {
		expect(
			cardsOf({ values: [{ name: 'Items', readings: [7, 9] }], sparkline: true })[0]
				.sparkline,
		).toBeUndefined()
	})

	it('draws the second run when there is one, not the two rows of a window', () => {
		// a windowed card's rows are one per window: the reading and what it is
		// held against. The trend inside the window is a run of its own.
		const card = cardsOf({
			values: [{ name: 'Items', readings: [40, 60] }],
			period: monthly,
			sparkline: true,
			sparklineSeries: { Items: [10, 20, 30] },
		})[0]
		expect(card.value).toBe(60)
		expect(card.sparkline).toEqual({ data: [10, 20, 30] })
	})

	it('draws nothing for a windowed card until its second run lands', () => {
		// Its own rows are the reading and what it is held against, so drawing
		// them made a two-point line that read as a trend.
		const card = cardsOf({
			values: [{ name: 'Items', readings: [40, 60] }],
			period: monthly,
			window: { span: 'month to date' },
			sparkline: true,
		})[0]
		expect(card.value).toBe(60)
		expect(card.sparkline).toBeUndefined()
	})

	it('reads each value off its own column of the second run', () => {
		const cards = cardsOf({
			values: [
				{ name: 'Items', readings: [60] },
				{ name: 'Revenue', readings: [900] },
			],
			period: monthly,
			sparkline: true,
			sparklineSeries: { Items: [10, 20], Revenue: [300, 600] },
		})
		expect(cards.map((card: any) => card.sparkline.data)).toEqual([
			[10, 20],
			[300, 600],
		])
	})
})

describe('drilling into a reading', () => {
	it('names the value the reader pointed at, and the row it was read off', () => {
		const input = numberChart({
			values: [{ name: 'Revenue', readings: [200, 300] }],
			period: monthly,
		})

		expect(adaptChart(input)!.drillDown!.cardClick({ column: 'Revenue' })).toEqual({
			column: 'Revenue',
			row: input.result.rows[1],
		})
	})
})

describe('the rows a Number cell takes', () => {
	const rowsFor = (spec: NumberChartSpec) =>
		numberCardRows(numberChart(spec).config as NumberChartConfig, spec.column)

	it('is answered for the reading the cell names, not for the chart', () => {
		const spec: NumberChartSpec = {
			values: [
				{ name: 'Revenue', readings: [100] },
				{ name: 'Profit', readings: [40], comparison: { source: 'previous' } },
			],
			period: monthly,
		}
		expect(rowsFor({ ...spec, column: 'Revenue' })).toBe(4)
		expect(rowsFor({ ...spec, column: 'Profit' })).toBe(5)
	})

	it('is a title and a reading when nothing stands under them', () => {
		expect(rowsFor({ values: [revenue] })).toBe(4)
	})

	it('adds the delta row for a reading that is compared with something', () => {
		expect(
			rowsFor({
				values: [{ ...revenue, comparison: { source: 'previous' } }],
				period: monthly,
			}),
		).toBe(5)
	})

	it('adds the sparkline band under that, compared or not', () => {
		expect(rowsFor({ values: [revenue], period: monthly, sparkline: true })).toBe(7)
	})

	it('draws no sparkline band without a Dimension to run the trend along', () => {
		expect(rowsFor({ values: [revenue], sparkline: true })).toBe(4)
	})

	it('leaves every card less than a row of slack', () => {
		// What picks the row height: the three heights the card has, and how much
		// of the last row each of them wastes.
		for (const [rows, height] of [
			[4, 85.95],
			[5, 107.95],
			[7, 147.95],
		]) {
			expect(rows * ROW_HEIGHT).toBeGreaterThanOrEqual(height)
			expect(rows * ROW_HEIGHT - height).toBeLessThan(ROW_HEIGHT)
		}
	})
})

describe('the reading a dashboard cell names', () => {
	const three: NumberChartSpec = {
		values: [
			{ name: 'Revenue', readings: [100], color: '#2490EF' },
			{ name: 'Profit', readings: [40] },
			{ name: 'Items', readings: [7] },
		],
	}

	it('is the only card the cell draws', () => {
		const cards = cardsOf({ ...three, column: 'Profit' })
		expect(cards).toHaveLength(1)
		expect(cards[0]).toMatchObject({ title: 'Profit', value: 40, column: 'Profit' })
	})

	it('carries the settings that stand beside that reading, not another one', () => {
		expect(cardsOf({ ...three, column: 'Profit' })[0].color).toBeUndefined()
		expect(cardsOf({ ...three, column: 'Revenue' })[0].color).toBe('#2490EF')
	})

	it('is the first reading when the cell names none', () => {
		// A cell written before a cell could name a reading draws what it drew.
		expect(cardsOf({ ...three, column: undefined })[0].title).toBe('Revenue')
	})

	it('drills into the reading the cell names', () => {
		const input = { ...numberChart({ ...three, column: 'Items' }) }
		expect(adaptChart(input)!.drillDown!.cardClick({ column: 'Items' })).toEqual({
			column: 'Items',
			row: input.result.rows[0],
		})
	})
})

describe('a cell naming a reading the Chart no longer states', () => {
	const gone = () => cardsOf({ values: [{ name: 'Revenue', readings: [100] }], column: 'Margin' })

	it('draws the card that named it, so the reader is told which one went', () => {
		expect(gone()).toHaveLength(1)
		expect(gone()[0]).toMatchObject({ column: 'Margin', title: 'Margin', missing: true })
	})

	it('states no reading, rather than the one that took its place', () => {
		expect(gone()[0].value).toBeNull()
	})
})
