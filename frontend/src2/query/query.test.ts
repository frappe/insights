import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import type { AdhocFilters } from '../types/query.types'

const calls = vi.hoisted(() => [] as any[])

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: (method: string, args: any) => {
		calls.push({ method, args })
		return Promise.resolve({ message: {} })
	},
}))

import { makeAdhocQuery } from './query'

// The total is fetched under a query, and adhoc filters are one of the
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
	// @feature query.row-count
	it('is retired when the reader filters, not only when the pipeline changes', async () => {
		const query = makeAdhocQuery()
		query.result.totalRowCount = 120
		query.currentPage = 3

		query.adhocFilters = filtersOn('region')
		await nextTick()

		expect(query.result.totalRowCount).toBe(0)
		expect(query.currentPage).toBe(1)
	})

	// @feature query.row-count
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

// The footer's page numbers are the query's, not the table's: a page is fetched
// and not sliced, so turning to one is a run.

const ordersTable = {
	table: { type: 'table' as const, data_source: 'demo', table_name: 'orders' },
}

function executionsSent() {
	return calls.filter((c) => c.args.method === 'execute').map((c) => c.args.args.page)
}

beforeEach(() => {
	calls.length = 0
})

describe('the page of rows a reader is reading', () => {
	// @feature query.result-pagination
	it('turns to the page asked for and asks the server for its rows, never for a page before the first', async () => {
		const query = makeAdhocQuery()
		query.setSource(ordersTable)
		await query.execute()
		expect(executionsSent()).toEqual([1])

		query.goToPage(2)
		await nextTick()
		expect(query.currentPage).toBe(2)
		await vi.waitFor(() => expect(executionsSent()).toEqual([1, 2]))

		query.goToPage(0)
		await nextTick()
		expect(query.currentPage).toBe(2)
		expect(executionsSent()).toEqual([1, 2])
	})
})

// Undo walks the whole pipeline, and an open operation editor holds one of its
// steps: stepping the pipeline out from under the dialog leaves the dialog
// writing an operation that is no longer there.

describe('an author stepping back through the pipeline', () => {
	beforeEach(() => vi.useFakeTimers())
	afterEach(() => vi.useRealTimers())

	// @feature query.undo-redo
	it('undoes the last pipeline edit and redoes it, but not while an operation is open', async () => {
		const query = makeAdhocQuery()

		query.setSource(ordersTable)
		await nextTick()
		vi.advanceTimersByTime(500)

		query.addFilterGroup({
			logical_operator: 'And',
			filters: [
				{
					column: { type: 'column', column_name: 'order_status' },
					operator: '=',
					value: 'canceled',
				},
			],
		})
		await nextTick()
		vi.advanceTimersByTime(500)
		expect(query.doc.operations.map((o) => o.type)).toEqual(['source', 'filter_group'])

		query.history.undo()
		expect(query.doc.operations.map((o) => o.type)).toEqual(['source'])

		query.history.redo()
		expect(query.doc.operations.map((o) => o.type)).toEqual(['source', 'filter_group'])

		expect(query.canUndo()).toBe(true)
		query.setActiveEditIndex(1)
		expect(query.canUndo()).toBe(false)
		expect(query.canRedo()).toBe(false)
	})
})
