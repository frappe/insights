import { describe, expect, it } from 'vitest'
import { numberChart, type NumberChartSpec } from './fixtures'
import { adaptChart } from './index'
import NumberCards from './NumberCards.vue'

function adapt(spec: NumberChartSpec) {
	const filler = adaptChart(numberChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const cardsOf = (spec: NumberChartSpec) => adapt(spec).props.cards

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
		expect(adapt({ values: [{ name: 'Revenue', readings: [100] }] }).card).toBe(false)
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
		// v2 prints a number; what the number means stays the caller's.
		const card = cardsOf({ values: [{ name: 'Margin', readings: [0.42], percent: true }] })[0]
		expect(card.value).toBe(42)
		expect(card.suffix).toBe('%')
	})
})

describe('the comparison', () => {
	const monthly: NumberChartSpec = {
		values: [{ name: 'Revenue', readings: [200, 300] }],
		period: { name: 'created_at', type: 'Datetime', granularity: 'month' },
		comparison: true,
	}

	it('derives the change from the reading before it, as a percentage', () => {
		// v2 takes a computed delta and prints it. The arithmetic is the caller's.
		const card = cardsOf(monthly)[0]
		expect(card.delta).toBe(50)
		expect(card.deltaSuffix).toBe('%')
	})

	it('says what the change is measured against, at the grain it was grouped by', () => {
		expect(cardsOf(monthly)[0].deltaCaption).toBe('vs previous month')
	})

	it('signs the change the way the data moved, and leaves the reading to v2', () => {
		// The card flips its colors for a metric where a fall is good news, so
		// flipping the number here as well would flip it back.
		const card = cardsOf({
			values: [{ name: 'Churn', readings: [300, 200] }],
			period: { name: 'created_at', type: 'Datetime', granularity: 'month' },
			comparison: true,
			negativeIsBetter: true,
		})[0]
		expect(card.delta).toBeCloseTo(-33.33, 2)
		expect(card.negativeIsBetter).toBe(true)
	})

	it('states no change when there is nothing to measure one from', () => {
		expect(
			cardsOf({
				values: [{ name: 'Revenue', readings: [300] }],
				period: { name: 'created_at', type: 'Datetime', granularity: 'month' },
				comparison: true,
			})[0].delta,
		).toBeNull()
		// A change from zero has no percentage.
		expect(
			cardsOf({
				values: [{ name: 'Revenue', readings: [0, 300] }],
				period: { name: 'created_at', type: 'Datetime', granularity: 'month' },
				comparison: true,
			})[0].delta,
		).toBeNull()
	})

	it('states none at all on a Chart that compares nothing', () => {
		const card = cardsOf({ values: [{ name: 'Revenue', readings: [200, 300] }] })[0]
		expect(card.delta).toBeUndefined()
		expect(card.deltaCaption).toBeUndefined()
	})
})

describe('the sparkline', () => {
	it('carries every reading, oldest first, and the color the Chart chose', () => {
		const card = cardsOf({
			values: [{ name: 'Items', readings: [7, 9, 8] }],
			period: { name: 'created_at', type: 'Datetime', granularity: 'month' },
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
})

describe('drilling into a reading', () => {
	it('names the value the reader pointed at, and the row it was read off', () => {
		const input = numberChart({
			values: [{ name: 'Revenue', readings: [200, 300] }],
			period: { name: 'created_at', type: 'Datetime', granularity: 'month' },
		})

		expect(adaptChart(input)!.drillDown!.cardClick({ column: 'Revenue' })).toEqual({
			column: 'Revenue',
			row: input.result.rows[1],
		})
	})
})
