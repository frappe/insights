import { describe, expect, it } from 'vitest'
import { EMPTY_RESULT } from '../../query/helpers'
import { fetchTiming } from './status'

const result = (patch: Partial<typeof EMPTY_RESULT>) => ({ ...EMPTY_RESULT, ...patch })

describe('fetchTiming', () => {
	it('says nothing about a result that never ran', () => {
		expect(fetchTiming(result({}))).toBe('')
	})

	it('names the cache instead of a duration', () => {
		expect(fetchTiming(result({ executedSQL: 'select 1', timeTaken: -1 }))).toBe('from cache')
	})

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
