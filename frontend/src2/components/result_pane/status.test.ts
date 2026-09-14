import { describe, expect, it } from 'vitest'
import { emptyResult } from '../../query/helpers'
import type { QueryResult } from '../../types/query.types'
import { fetchTiming } from './status'

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
