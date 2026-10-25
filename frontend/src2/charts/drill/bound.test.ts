import { describe, expect, it } from 'vitest'
import { levelBound } from './bound'

describe('the line under a drill level', () => {
	// @feature charts.drill-breakdown
	it('names the groups a ranked breakdown was cut to', () => {
		expect(levelBound({ breakdown: true, ordered: false, shown: 20, total: 1240 })).toBe(
			'top 20 of 1,240 groups',
		)
	})

	// @feature charts.drill-breakdown
	it('names the stretch an ordered breakdown was cut to', () => {
		expect(levelBound({ breakdown: true, ordered: true, shown: 20, total: 96 })).toBe(
			'latest 20 of 96 periods',
		)
	})

	// @feature charts.drill-breakdown
	it('says nothing about a breakdown that came back whole', () => {
		expect(levelBound({ breakdown: true, ordered: false, shown: 7, total: 7 })).toBe('')
		expect(levelBound({ breakdown: true, ordered: false, shown: 7 })).toBe('')
	})

	// @feature charts.drill-rows-state
	it('leaves the rows level to the pane that pages it', () => {
		expect(levelBound({ breakdown: false, ordered: false, shown: 100, total: 1240 })).toBe('')
	})
})
