import { FunnelChart } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import { funnelChart, type FunnelChartSpec } from './fixtures'
import { adaptChart } from './index'

function adapt(spec: FunnelChartSpec) {
	const filler = adaptChart(funnelChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const propsOf = (spec: FunnelChartSpec) => adapt(spec).props

const lifecycle = [
	{ stage: 'Ordered', value: 1000 },
	{ stage: 'Shipped', value: 800 },
	{ stage: 'Delivered', value: 600 },
]

describe('a funnel built from one row per stage', () => {
	it('names the stage column and the value column, and hands the rows over', () => {
		const input = funnelChart({
			title: 'Order lifecycle',
			dimension: 'status',
			measure: 'items',
			stages: lifecycle,
		})
		const { component, props } = adaptChart(input)!

		expect(component).toBe(FunnelChart)
		expect(props.title).toBe('Order lifecycle')
		expect(props.category).toBe('status')
		expect(props.value).toBe('items')
		expect(props.data).toBe(input.result.rows)
	})

	it('prints the conversion rate unless the Chart switched it off', () => {
		// It is what a funnel is read for, and v2 prints it by default, so only
		// the Chart that turned it off has anything to say.
		expect(
			propsOf({ dimension: 'status', measure: 'items', stages: lifecycle }).showPercentages,
		).toBeUndefined()
		expect(
			propsOf({
				dimension: 'status',
				measure: 'items',
				stages: lifecycle,
				showPercentage: false,
			}).showPercentages,
		).toBe(false)
	})

	it('draws nothing until the Chart names both columns', () => {
		expect(
			adaptChart(funnelChart({ dimension: 'status', stages: lifecycle })),
		).toBeUndefined()
		expect(adaptChart(funnelChart({ measure: 'items', stages: lifecycle }))).toBeUndefined()
	})
})

describe('a funnel built from several Measures on one row', () => {
	it('turns the one row on its side, one row per stage', () => {
		// v2 reads a stage column and a value column, and the Measures shape has
		// neither: the stages stand side by side on a single row. Reshaping data
		// into the picture it is drawn as is the caller's, so it happens here.
		const props = propsOf({ measures: lifecycle })

		expect(props.data).toEqual([
			{ [props.category]: 'Ordered', [props.value]: 1000 },
			{ [props.category]: 'Shipped', [props.value]: 800 },
			{ [props.category]: 'Delivered', [props.value]: 600 },
		])
	})

	it('takes the Measures over the grouped columns when the Chart carries both', () => {
		const props = propsOf({
			dimension: 'status',
			measure: 'items',
			stages: lifecycle,
			measures: lifecycle,
		})
		expect(props.category).not.toBe('status')
		expect(props.data).toHaveLength(3)
	})
})

describe('drilling into a stage', () => {
	it('names the value column and the row the stage was drawn from', () => {
		const input = funnelChart({ dimension: 'status', measure: 'items', stages: lifecycle })
		const row = input.result.rows[1]

		expect(
			adaptChart(input)!.drillDown!.stageClick({
				label: 'Shipped',
				value: 800,
				index: 1,
				row,
			}),
		).toEqual({ column: 'items', row })
	})

	it('names the Measure behind a stage, and the one row every stage was read off', () => {
		const input = funnelChart({ measures: lifecycle })
		const filler = adaptChart(input)!

		expect(
			filler.drillDown!.stageClick({
				label: 'Shipped',
				value: 800,
				index: 1,
				row: filler.props.data[1],
			}),
		).toEqual({ column: 'Shipped', row: input.result.rows[0] })
	})
})
