import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Filter } from '../../components/filter_picker/filter_picker'
import type { DrillLevelData, DrillRowFilter, DrillRowsState } from './drill_stack'
import { makeDrillRows } from './rows_view'

// The rows level in a View. A View never receives the pipeline, so the server
// applies the filters, sort, find and page.

const columns = [
	{ name: 'name', type: 'String' as const },
	{ name: 'customer', type: 'String' as const },
	{ name: 'total', type: 'Decimal' as const },
]

function answer(over: Partial<DrillLevelData> = {}): DrillLevelData {
	return {
		columns,
		rows: [{ name: 'SAL-ORD-0001', customer: 'Chetak Traders', total: 1200 }],
		total_row_count: 1240,
		record_links: { name: 'Sales Order' },
		can_export: true,
		...over,
	}
}

// A state arrives holding Vue reactive arrays, which structured clone rejects.
// So the test records a plain copy.
const copyOf = (state: DrillRowsState): DrillRowsState => JSON.parse(JSON.stringify(state))

/** The filter picker holds a whole column, not a column name. */
function rule(column: string, operator: any, value: any): Filter {
	return {
		column: columns.find((c) => c.name === column)!,
		operator,
		value,
	}
}

function server(...answers: DrillLevelData[]) {
	const asked: DrillRowsState[] = []
	const downloads: { state: DrillRowsState; format: string }[] = []
	const valueRequests: { column: string; search: string; rules: DrillRowFilter[] }[] = []
	let next = 0
	return {
		asked,
		downloads,
		valueRequests,
		values: (column: string, search: string, rules: DrillRowFilter[]) => {
			valueRequests.push({ column, search, rules: JSON.parse(JSON.stringify(rules)) })
			return Promise.resolve(['Chetak Traders'])
		},
		range: () => Promise.resolve(undefined),
		read: (state: DrillRowsState) => {
			asked.push(copyOf(state))
			return Promise.resolve(answers[next++] ?? answers[answers.length - 1] ?? answer())
		},
		download: (state: DrillRowsState, format: string) => {
			downloads.push({ state: copyOf(state), format })
			// never resolves: the tests check only the call
			return new Promise<string>(() => {})
		},
	}
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0))

describe('the rows behind a segment, as a reader reads them', () => {
	beforeEach(() => {
		vi.useFakeTimers({ shouldAdvanceTime: true })
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	// @feature charts.drill-rows-state
	it('renders the answer the dialog already holds without asking for another', () => {
		const source = server()
		const rows = makeDrillRows(answer(), source)

		expect(source.asked).toEqual([])
		expect(rows.ready).toBe(true)
		expect(rows.result.rows).toHaveLength(1)
		expect(rows.result.totalRowCount).toBe(1240)
		expect(rows.result.formattedRows).toHaveLength(1)
		expect(rows.pageSize).toBe(100)
	})

	// @feature charts.drill-rows-state
	it('asks for the rows run by the column just sorted, with the earlier sort behind it', async () => {
		const source = server()
		const rows = makeDrillRows(answer(), source)

		rows.addOrderBy!({ column: { type: 'column', column_name: 'total' }, direction: 'desc' })
		await flush()
		rows.addOrderBy!({ column: { type: 'column', column_name: 'customer' }, direction: 'asc' })
		await flush()

		expect(source.asked.at(-1)!.sort).toEqual([
			{ column: 'customer', direction: 'asc' },
			{ column: 'total', direction: 'desc' },
		])
		expect(rows.currentOperations).toEqual([
			{
				type: 'order_by',
				column: { type: 'column', column_name: 'customer' },
				direction: 'asc',
			},
			{
				type: 'order_by',
				column: { type: 'column', column_name: 'total' },
				direction: 'desc',
			},
		])
	})

	// @feature charts.drill-rows-state
	it('drops a sort the reader cleared', async () => {
		const source = server()
		const rows = makeDrillRows(answer(), source)

		rows.addOrderBy!({ column: { type: 'column', column_name: 'total' }, direction: 'desc' })
		await flush()
		rows.removeOrderBy!('total')
		await flush()

		expect(source.asked.at(-1)!.sort).toEqual([])
	})

	// @feature charts.drill-rows-state
	it('waits for the reader to stop typing before it asks the find', async () => {
		const source = server()
		const rows = makeDrillRows(answer(), source)

		rows.setFind!('che')
		rows.setFind!('chetak')
		expect(rows.findTerm).toBe('chetak')
		expect(source.asked).toEqual([])

		await vi.advanceTimersByTimeAsync(400)

		expect(source.asked).toHaveLength(1)
		expect(source.asked[0].find).toBe('chetak')
	})

	// @feature charts.drill-rows-state
	it('takes a narrowed or reordered result from its first page', async () => {
		const source = server()
		const rows = makeDrillRows(answer(), source)

		rows.goToPage!(4)
		await flush()
		expect(source.asked.at(-1)!.page).toBe(4)

		rows.setFind!('chetak')
		await vi.advanceTimersByTimeAsync(400)

		expect(source.asked.at(-1)!.page).toBe(1)
	})

	// @feature charts.drill-rows-state
	it('keeps the sort and the find on every page it turns to', async () => {
		const source = server()
		const rows = makeDrillRows(answer(), source)

		rows.addOrderBy!({ column: { type: 'column', column_name: 'total' }, direction: 'desc' })
		rows.setFind!('chetak')
		await vi.advanceTimersByTimeAsync(400)
		rows.goToPage!(3)
		await flush()

		expect(source.asked.at(-1)).toEqual({
			row_filters: [],
			sort: [{ column: 'total', direction: 'desc' }],
			find: 'chetak',
			page: 3,
		})
	})

	// @feature charts.drill-rows-filter
	it('asks the server for the rows the reader’s own rules leave, from their first page', async () => {
		const source = server()
		const rows = makeDrillRows(answer(), source)

		rows.goToPage!(4)
		await flush()
		rows.setFilters([rule('customer', 'in', ['Chetak Traders'])])
		await flush()

		expect(source.asked.at(-1)!.row_filters).toEqual([
			{ column: 'customer', operator: 'in', value: ['Chetak Traders'] },
		])
		// Filtered rows are a new result. Its page four means nothing to the reader.
		expect(source.asked.at(-1)!.page).toBe(1)
	})

	// @feature charts.drill-rows-filter charts.drill-rows-state
	it('holds the answer the reader’s own reading last asked for', async () => {
		// `BuilderDrillDown.vue` opens a level as a query from these `operations`.
		// So they must match the filtered rows on screen, not the first response.
		const filtered = answer({
			operations: [{ type: 'source' } as any, { type: 'filter' } as any],
		})
		const source = server(filtered)
		const rows = makeDrillRows(answer({ operations: [{ type: 'source' } as any] }), source)

		rows.setFilters([rule('customer', 'in', ['Chetak Traders'])])
		await flush()

		expect(rows.level.operations).toEqual(filtered.operations)
	})

	// @feature charts.drill-rows-filter
	it('leaves a rule out of the values its own column lists', async () => {
		const source = server()
		const rows = makeDrillRows(answer(), source)

		rows.setFilters([rule('customer', 'in', ['Chetak Traders']), rule('total', '>', 100)])
		await flush()
		await rows.valuesProvider(columns[1])('che')

		// The rule on this column leaves only its own value in the rows. Applied to
		// the value list, it would hide every other value from the picker.
		expect(source.valueRequests).toEqual([
			{
				column: 'customer',
				search: 'che',
				rules: [{ column: 'total', operator: '>', value: 100 }],
			},
		])
	})

	// @feature charts.drill-record-link
	it('reads the record links off the answer it is rendering', async () => {
		const source = server(answer({ record_links: { name: 'Sales Invoice' } }))
		const rows = makeDrillRows(answer(), source)

		expect(rows.recordLinks).toEqual({ name: 'Sales Order' })

		rows.goToPage!(2)
		await flush()

		expect(rows.recordLinks).toEqual({ name: 'Sales Invoice' })
	})

	// @feature charts.drill-rows-state
	it('drops an answer a newer question has already superseded', async () => {
		const slow = answer({ rows: [{ name: 'STALE', customer: 'x', total: 1 }] })
		const fresh = answer({ rows: [{ name: 'FRESH', customer: 'y', total: 2 }] })
		const source = server(slow, fresh)
		const rows = makeDrillRows(answer(), source)

		rows.goToPage!(2)
		rows.goToPage!(3)
		await flush()

		expect(source.asked.map((state) => state.page)).toEqual([2, 3])
		expect(rows.result.rows[0].name).toBe('FRESH')
		expect(rows.executing).toBe(false)
	})

	// @feature charts.drill-rows-export
	it('allows export only where the server said the reader may export', () => {
		const source = server()

		expect(makeDrillRows(answer({ can_export: false }), source).exportResults).toBeUndefined()

		const rows = makeDrillRows(answer(), source)
		rows.addOrderBy!({ column: { type: 'column', column_name: 'total' }, direction: 'desc' })
		rows.setFilters([rule('customer', 'in', ['Chetak Traders'])])
		rows.exportResults!('csv', 'export_1_1_2026')

		expect(source.downloads).toEqual([
			{
				state: {
					row_filters: [
						{ column: 'customer', operator: 'in', value: ['Chetak Traders'] },
					],
					sort: [{ column: 'total', direction: 'desc' }],
					find: '',
					page: 1,
				},
				format: 'csv',
			},
		])
	})
})
