import { describe, expect, it } from 'vitest'
import { computed } from 'vue'
import { emptyResult } from '../../query/helpers'
import type { QueryResult } from '../../types/query.types'
import { fetchTiming, knownRowCount, rangeAroundCount, rowCountText } from './status'

const result = (patch: Partial<QueryResult>) => ({ ...emptyResult(), ...patch })

describe('fetchTiming', () => {
	// @feature query.result-timing
	it('says nothing about a result that never ran', () => {
		expect(fetchTiming(result({}))).toBe('')
	})

	// @feature query.result-timing
	it('names the cache instead of a duration', () => {
		expect(fetchTiming(result({ executedSQL: 'select 1', timeTaken: -1 }))).toBe('from cache')
	})

	// @feature query.result-timing
	it('prints a duration without trailing zeros', () => {
		expect(fetchTiming(result({ executedSQL: 'select 1', timeTaken: 1.2 }))).toBe(
			'fetched in 1.2s',
		)
		expect(fetchTiming(result({ executedSQL: 'select 1', timeTaken: 0.023 }))).toBe(
			'fetched in 0.02s',
		)
		expect(fetchTiming(result({ executedSQL: 'select 1', timeTaken: 2 }))).toBe('fetched in 2s')
	})
})

const page = (to: number, isLastPage: boolean) => ({
	to: computed(() => to),
	isLastPage: computed(() => isLastPage),
})

describe('knownRowCount', () => {
	// @feature query.row-count
	it('takes a last page short of a full one as the whole result', () => {
		expect(knownRowCount({ loadedCount: 1, fetchable: true, paging: page(1, true) })).toBe(1)
	})

	// @feature query.row-count
	it('leaves the count unknown while more rows may follow', () => {
		expect(
			knownRowCount({ loadedCount: 100, fetchable: true, paging: page(100, false) }),
		).toBeUndefined()
	})

	// @feature query.row-count
	it('prefers the count the server reported', () => {
		expect(
			knownRowCount({
				totalRowCount: 2345,
				loadedCount: 100,
				fetchable: true,
				paging: page(100, false),
			}),
		).toBe(2345)
	})
})

describe('row count copy', () => {
	// @feature query.row-count
	it('says one row in the singular', () => {
		expect(rowCountText(1)).toBe('Showing 1 row')
		expect(rowCountText(2)).toBe('Showing 2 rows')
	})

	// @feature query.row-count
	it('cuts the range sentence where the count goes', () => {
		expect(rangeAroundCount(1, 100)).toEqual(['Showing 1–100 of', 'rows'])
	})
})
