import { describe, expect, it } from 'vitest'
import { numberChart, type NumberChartSpec } from './fixtures'
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

describe('a Number Chart with several values', () => {
	it('lays the readings out itself, one card behind each of them', () => {
		// v2's card is one reading and a Number Chart is several, so the grid is
		// Insights' own. It draws no chrome: the card around it is the one every
		// other chart type gets.
		const { component, props } = adapt({
			values: [
				{ name: 'Revenue', readings: [100] },
				{ name: 'Profit', readings: [40] },
				{ name: 'Items', readings: [7] },
			],
		})

		expect(component).toBe(NumberCards)
		expect(props.cards.map((card: any) => card.title)).toEqual([
			'Revenue',
			'Profit',
			'Items',
		])
		expect(props.cards.map((card: any) => card.value)).toEqual([100, 40, 7])
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
			values: [{ name: 'Revenue', readings: [12300] }, { name: 'Items', readings: [7], decimal: 0 }],
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
		expect(cardsOf({ values: [{ name: 'Revenue', readings: [300] }] })[0].target).toBeUndefined()
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
				{ name: 'Revenue', readings: [300], comparison: { source: 'constant', value: 250 } },
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
				values: [{ name: 'Revenue', readings: [0, 300], comparison: { source: 'previous' } }],
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
						{ source: 'measure', measure: measureNamed('Revenue_target'), show: 'attainment' },
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
			cardsOf({ values: [{ name: 'Items', readings: [7, 9] }], sparkline: true })[0].sparkline,
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
