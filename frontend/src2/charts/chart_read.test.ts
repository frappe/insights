import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
	makeChartRead,
	useSharedChart,
	type CardFilter,
	type ChartReadSurface,
	type DashboardFilterContext,
} from './chart_read'
import type { Filter } from '../components/filter_picker/filter_picker'

const calls = vi.hoisted(() => [] as any[])

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: (method: string, args: any) => {
		calls.push({ method, args })
		return Promise.resolve({ message: { columns: [], rows: [] } })
	},
}))

beforeEach(() => {
	calls.length = 0
})

// The card filter a table's filter row writes belongs to the read, not to the
// host drawing it: a row drawn on the builder's preview or behind a public link
// narrows the query that read runs, the same way a dashboard card's does. It
// used to depend on a holder only the dashboard provided, and the row vanished
// on every other surface.

const rule: Filter = {
	column: { name: 'region', type: 'String' },
	operator: 'contains',
	value: 'north',
}

function readOf(surface?: ChartReadSurface) {
	const contexts: (DashboardFilterContext | undefined)[] = []
	const read = makeChartRead(
		{
			doc: { name: 'chart-1', title: 'Sales', chart_type: 'Table', config: {} as any },
			fetchData: (_force, filterContext) => {
				contexts.push(filterContext)
				return Promise.resolve({ columns: [], rows: [] })
			},
			fetchDrillData: () => Promise.reject(new Error('not asked')),
		},
		surface,
	)
	return { read, contexts }
}

describe('a card filter on a read with no surface', () => {
	// @feature dashboard.card-filter
	it('narrows the read itself, naming the chart the rule lands on', async () => {
		const { read, contexts } = readOf()

		await read.load()
		expect(contexts).toEqual([undefined])

		read.applyCardFilters([rule])
		await vi.waitFor(() => expect(contexts).toHaveLength(2))

		expect(contexts[1]).toEqual({
			chart: 'chart-1',
			cardFilters: [{ column: 'region', operator: 'contains', value: 'north' }],
		})
	})

	// @feature charts.reset-filters
	it('holds the boxes the rule was typed in, so a reset can empty them', async () => {
		const { read } = readOf()

		expect(read.cardFilterText).toEqual({})
		read.cardFilterText = { region: 'north' }
		expect(read.cardFilterText).toEqual({ region: 'north' })
	})
})

describe('a card filter on a surface that holds its own', () => {
	// @feature dashboard.card-filter
	it('goes to the surface, and the read carries none of its own', async () => {
		const routed: [string, Filter[]][] = []
		const dashboardContext = (chart: string): DashboardFilterContext => ({
			chart,
			dashboard: 'dashboard-1',
			items: [],
			filters: {},
			cardFilters: [{ column: 'city', operator: '=', value: 'delhi' }],
		})
		const { read, contexts } = readOf({
			id: 'dashboard:dashboard-1',
			filterContext: dashboardContext,
			applyCardFilters: (chart_name, filters) => routed.push([chart_name, filters]),
		})

		read.applyCardFilters([rule])
		expect(routed).toEqual([['chart-1', [rule]]])
		expect(read.cardFilters).toEqual([])

		// the grid routes the rule into its own context, so nothing is sent twice
		await read.load()
		expect(contexts[0]?.cardFilters).toEqual([
			{ column: 'city', operator: '=', value: 'delhi' },
		])
	})
})

// A number card is drawn as one cell per reading, and every cell loads the
// chart it draws. On a public link the saved feed named no request, so nothing
// dropped the repeats and one card ran its query once per reading.

describe('the request a public read would send', () => {
	// @feature shared.read-once
	it('is asked once, however many cards load the same chart under the same filters', async () => {
		const chart = { doc: { name: 'chart-9', chart_type: 'Number', config: { limit: 100 } } }
		const read = useSharedChart(chart as any)

		await read.load()
		await read.load()

		expect(calls).toHaveLength(1)
	})

	// @feature shared.read-once
	it('is asked again when the surface narrows the chart differently', async () => {
		const cardFilters: CardFilter[] = []
		const chart = { doc: { name: 'chart-10', chart_type: 'Number', config: { limit: 100 } } }
		const read = useSharedChart(chart as any, {
			id: 'dashboard:dashboard-9',
			filterContext: (chart_name) => ({
				chart: chart_name,
				dashboard: 'dashboard-9',
				cardFilters: [...cardFilters],
			}),
		})

		await read.load()
		expect(calls).toHaveLength(1)

		cardFilters.push({ column: 'city', operator: '=', value: 'delhi' })
		await read.load()
		expect(calls).toHaveLength(2)
	})
})

// The rows on a card answer one question, and a load that would ask it again is
// dropped. A reader asking for fresh rows is not asking the same question — and
// a run that failed left nothing on screen, so asking again has to take back
// what the card said went wrong.

function readAnswering(answer: (attempt: number) => Promise<any>) {
	const forces: boolean[] = []
	let attempts = 0
	const read = makeChartRead({
		doc: { name: 'chart-2', title: 'Sales', chart_type: 'Table', config: {} as any },
		requestKey: () => 'the same question',
		fetchData: (force) => {
			forces.push(force)
			return answer(++attempts)
		},
		fetchDrillData: () => Promise.reject(new Error('not asked')),
	})
	return { read, forces }
}

const northThenSouth = (attempt: number) =>
	Promise.resolve({
		columns: [{ name: 'region', type: 'String' }],
		rows: [{ region: attempt === 1 ? 'North' : 'South' }],
	})

describe('a card asked for its rows again', () => {
	// @feature charts.refresh
	it('a refresh asks the server again, past the cache', async () => {
		const { read, forces } = readAnswering(northThenSouth)

		await read.load()
		expect(read.result.rows).toEqual([{ region: 'North' }])

		// the same question, so nothing is asked
		await read.load()
		expect(forces).toEqual([false])
		expect(read.result.rows).toEqual([{ region: 'North' }])

		await read.load(true)
		expect(forces).toEqual([false, true])
		expect(read.result.rows).toEqual([{ region: 'South' }])
	})

	// @feature charts.retry
	it('a retry after a failed run asks again and clears the error', async () => {
		const { read } = readAnswering((attempt) =>
			attempt === 1
				? Promise.reject(new Error('Table orders is gone'))
				: northThenSouth(attempt),
		)

		await read.load()
		expect(read.failed).toBe(true)
		expect(read.failure).toBe('Table orders is gone')
		expect(read.result.rows).toEqual([])

		await read.load()
		expect(read.failed).toBe(false)
		expect(read.failure).toBe('')
		expect(read.result.rows).toEqual([{ region: 'South' }])
	})
})
