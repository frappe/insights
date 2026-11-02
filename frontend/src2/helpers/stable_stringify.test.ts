import { describe, expect, it } from 'vitest'
import { stableStringify } from './stable_stringify'

describe('stableStringify', () => {
	// @feature charts.rename-while-saving
	it('serializes two objects that differ only in key order alike', () => {
		expect(stableStringify({ b: 1, a: 2 })).toBe(stableStringify({ a: 2, b: 1 }))
	})

	// @feature charts.rename-while-saving
	it('sorts the keys of a nested object too', () => {
		const sent = {
			config: { x_axis: { dimension: { column_name: 'creation', granularity: 'month' } } },
		}
		const answered = {
			config: { x_axis: { dimension: { granularity: 'month', column_name: 'creation' } } },
		}
		expect(stableStringify(sent)).toBe(stableStringify(answered))
	})

	// @feature charts.rename-while-saving
	it('keeps the order of an array, which is part of its value', () => {
		expect(stableStringify([1, 2])).not.toBe(stableStringify([2, 1]))
	})

	// @feature charts.rename-while-saving
	it('tells two different values apart', () => {
		expect(stableStringify({ a: 1 })).not.toBe(stableStringify({ a: 2 }))
	})
})
