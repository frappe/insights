import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createSSRApp, h, nextTick } from 'vue'
import { renderToString } from 'vue/server-renderer'
import type { AdhocFilters } from '../types/query.types'

const calls = vi.hoisted(() => [] as any[])
const server = vi.hoisted(() => ({
	refusal: null as Error | null,
	toasts: [] as string[],
	doc: null as any,
}))

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	toast: { error: (message: string) => server.toasts.push(message) },
	call: (method: string, args: any) => {
		calls.push({ method, args })
		if (server.refusal) return Promise.reject(server.refusal)
		if (method === 'insights.api.get_doc' && server.doc) return Promise.resolve(server.doc)
		return Promise.resolve({ message: {} })
	},
}))

import ChartQuerySelector from '../charts/components/ChartQuerySelector.vue'
import useQuery, { makeAdhocQuery, makeQuery } from './query'
import { stableStringify } from '../helpers/stable_stringify'

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
	server.refusal = null
	server.toasts.length = 0
})

describe('a run the server refuses', () => {
	// @feature query.execute-error
	it('states the refusal once, in the result pane', async () => {
		const query = makeAdhocQuery()
		query.setSource(ordersTable)
		const sentence = 'Operation 1 (sql): Failed to parse the SQL query'
		server.refusal = Object.assign(new Error('/api/method/run_doc_method QueryRefused'), {
			messages: [sentence],
		})

		await query.execute()

		expect(query.executionError).toBe(sentence)
		expect(server.toasts).toEqual([])
	})

	// @feature query.row-count
	it('answers a Load Count it refuses with the reason', async () => {
		const query = makeAdhocQuery()
		query.setSource(ordersTable)
		await query.execute()
		const sentence = 'Counting the rows timed out'
		server.refusal = Object.assign(new Error('/api/method/run_doc_method QueryTimeout'), {
			messages: [sentence],
		})

		await query.fetchResultCount()

		expect(server.toasts).toEqual([sentence])
		expect(query.result.totalRowCount).toBe(0)
	})

	// @feature query.execute-error
	it("is told beside a chart's query picker, where no result pane shows it", async () => {
		const sentence = 'Operation 1 (sql): Failed to parse the SQL query'
		useQuery('query-failing').executionError = sentence
		const app = createSSRApp({
			render: () =>
				h(ChartQuerySelector, {
					modelValue: 'query-failing',
					queries: [{ label: 'Failing', value: 'query-failing' }],
				}),
		})
		app.component('Combobox', { render: () => h('div') })
		app.config.globalProperties.__ = (text: string) => text
		app.config.warnHandler = () => {}

		expect(await renderToString(app)).toContain(sentence)
	})

	// @feature query.execute-error
	it('says the server stayed busy, rather than that the query found nothing', async () => {
		vi.useFakeTimers()
		try {
			const query = makeAdhocQuery()
			query.setSource(ordersTable)
			const sentence = 'The server is busy. Try again in a moment.'
			server.refusal = Object.assign(
				new Error('/api/method/run_doc_method ServiceUnavailableError'),
				{
					status: 503,
					exc_type: 'ServiceUnavailableError',
					messages: [sentence],
				},
			)

			const run = query.execute()
			await vi.runAllTimersAsync()
			await run

			expect(query.executionError).toBe(sentence)
			expect(server.toasts).toEqual([])
		} finally {
			vi.useRealTimers()
		}
	})
})

describe('a script the author runs', () => {
	// @feature query.script
	it('runs as the editor holds it, though the pause that writes it has not passed', async () => {
		const query = makeAdhocQuery()
		query.setCode({ code: "results = [{'n': 1}]" })

		await query.runCode({ code: "results = [{'m': 2}]" })

		const run = calls.find((c) => c.args.method === 'execute')
		expect(run.args.docs.operations).toEqual([{ type: 'code', code: "results = [{'m': 2}]" }])
	})
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

	// @feature query.undo-redo
	it('takes back one step per press, whatever the saves in between replaced', async () => {
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

		// a save's reply: the same pipeline under a new timestamp, its keys sorted
		// as the server stores JSON
		const reply = (modified: string) =>
			({
				...query.doc,
				modified,
				operations: JSON.parse(stableStringify(query.doc.operations)),
			}) as typeof query.doc
		query.doc = reply('2026-10-25 10:00:00')
		await nextTick()
		vi.advanceTimersByTime(500)
		// looking at an earlier step changes no step
		query.setActiveOperation(0)
		await nextTick()
		vi.advanceTimersByTime(500)

		query.history.undo()
		expect(query.doc.operations.map((o) => o.type)).toEqual(['source'])

		query.doc = reply('2026-10-25 10:00:01')
		await nextTick()
		vi.advanceTimersByTime(500)

		query.history.redo()
		expect(query.doc.operations.map((o) => o.type)).toEqual(['source', 'filter_group'])
	})

	// @feature query.undo-redo
	it('has nothing to undo in a saved query just opened', async () => {
		server.doc = {
			doctype: 'Insights Query v3',
			name: 'saved-query',
			operations: JSON.stringify([{ type: 'source', table: ordersTable }]),
		}
		const query = makeQuery('saved-query')
		await query.load()
		server.doc = null
		await nextTick()
		vi.advanceTimersByTime(500)

		query.history.undo()

		expect(query.doc.operations.map((o) => o.type)).toEqual(['source'])
	})
})
