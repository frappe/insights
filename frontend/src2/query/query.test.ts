import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import type { AdhocFilters } from '../types/query.types'

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: () => Promise.resolve({ message: {} }),
}))

import { makeAdhocQuery } from './query'

// The total is fetched under a query, and the filter row writes one of the
// query's two halves. A count left standing over a narrowed result states a
// total nothing produced, and keeps "Next" live onto an empty page.

function filtersOn(column: string): AdhocFilters {
	return {
		'query-1': {
			type: 'filter_group',
			logical_operator: 'And',
			filters: [
				{
					column: { type: 'column', column_name: column },
					operator: 'contains',
					value: 'north',
				},
			],
		},
	}
}

describe('the total row count', () => {
	it('is retired when the reader filters, not only when the pipeline changes', async () => {
		const query = makeAdhocQuery()
		query.result.totalRowCount = 120
		query.currentPage = 3

		query.adhocFilters = filtersOn('region')
		await nextTick()

		expect(query.result.totalRowCount).toBe(0)
		expect(query.currentPage).toBe(1)
	})

	it('stands while nothing the count was fetched under moves', async () => {
		const query = makeAdhocQuery()
		query.adhocFilters = filtersOn('region')
		await nextTick()

		query.result.totalRowCount = 120
		query.currentPage = 3
		await nextTick()

		expect(query.result.totalRowCount).toBe(120)
		expect(query.currentPage).toBe(3)
	})
})
