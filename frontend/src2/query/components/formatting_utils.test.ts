import { describe, expect, it } from 'vitest'
import { rulesByColumn, type FormattingMode } from './formatting_utils'

const PIVOT = ['category', 'Revenue___Men', 'Items___Men', 'Revenue___Women', 'Items___Women']

const rule = (columnName: string) =>
	({
		mode: 'color_scale',
		column: { column_name: columnName },
		value: undefined,
	}) as unknown as FormattingMode

describe('routing a rule to its columns', () => {
	it('names the drawn column itself', () => {
		expect(Object.keys(rulesByColumn([rule('Revenue___Women')], PIVOT))).toEqual([
			'Revenue___Women',
		])
	})

	it('names the measure behind every one of a pivot column', () => {
		expect(Object.keys(rulesByColumn([rule('Revenue')], PIVOT))).toEqual([
			'Revenue___Men',
			'Revenue___Women',
		])
	})

	it('names the dimension value one pivot column stands for', () => {
		expect(Object.keys(rulesByColumn([rule('Women')], PIVOT))).toEqual([
			'Revenue___Women',
			'Items___Women',
		])
	})

	it('paints nothing when it names nothing', () => {
		expect(rulesByColumn([rule('Profit')], PIVOT)).toEqual({})
		expect(rulesByColumn([rule('Revenue___Other')], PIVOT)).toEqual({})
	})

	it('matches a plain column when the table does not pivot', () => {
		expect(Object.keys(rulesByColumn([rule('Revenue')], ['category', 'Revenue']))).toEqual([
			'Revenue',
		])
	})

	it('stacks every rule that names a column', () => {
		const rules = [rule('Revenue'), rule('Revenue___Women')]
		expect(rulesByColumn(rules, PIVOT)['Revenue___Women']).toHaveLength(2)
		expect(rulesByColumn(rules, PIVOT)['Revenue___Men']).toHaveLength(1)
	})

	it('has nothing to route without rules', () => {
		expect(rulesByColumn(undefined, PIVOT)).toEqual({})
		expect(rulesByColumn([], PIVOT)).toEqual({})
	})
})
