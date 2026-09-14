import { describe, expect, it, vi } from 'vitest'
import type { Filter } from '../components/filter_picker/filter_picker'

// The store reads a document and draws cards, and neither is what a card filter
// is about: the browser the module is written for is stubbed down to what the
// store touches while it is built.
vi.hoisted(() => {
	const stub: any = {
		setTimeout: globalThis.setTimeout.bind(globalThis),
		clearTimeout: globalThis.clearTimeout.bind(globalThis),
		addEventListener() {},
		removeEventListener() {},
		innerWidth: 1400,
		innerHeight: 900,
		localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
		document: { createElement: () => ({ style: {} }) },
	}
	;(globalThis as any).window = stub
	;(globalThis as any).document = stub.document
	;(globalThis as any).localStorage = stub.localStorage
})

vi.mock('../router', () => ({
	default: { push() {}, resolve: () => ({ href: '/' }) },
}))

// A card filter is a list here; what the card does with it is the read's, and a
// read with no document to run against rejects.
vi.mock('../charts/chart_preview', () => ({
	default: () => ({ executionPriority: undefined, load() {} }),
}))

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: () => Promise.resolve({ message: {} }),
}))

import useDashboard from './dashboard'

// A card has two filter controls, the picker in its title row and the table's
// filter row, and each states only its own rules. Held as one list, the row
// wrote the boxes back over the picker's rules and the card silently counted
// the rows a stated filter excluded.

const status: Filter = {
	column: { name: 'status', type: 'String' },
	operator: '=',
	value: 'Open',
}
const region: Filter = {
	column: { name: 'region', type: 'String' },
	operator: 'contains',
	value: 'north',
}

let counter = 0
function newDashboard() {
	return useDashboard(`new-dashboard-${++counter}`)
}

describe('what narrows a card', () => {
	it('is both controls, whichever the reader wrote last', () => {
		const dashboard = newDashboard()

		dashboard.setCardFilters('chart-1', 'picker', [status])
		dashboard.setCardFilters('chart-1', 'row', [region])

		expect(dashboard.cardFiltersOn('chart-1')).toEqual([status, region])
	})

	it('keeps what the row stated when the picker is written', () => {
		const dashboard = newDashboard()

		dashboard.setCardFilters('chart-1', 'row', [region])
		dashboard.setCardFilters('chart-1', 'picker', [status])

		expect(dashboard.cardFiltersOn('chart-1')).toEqual([status, region])
	})

	it('is one card at a time', () => {
		const dashboard = newDashboard()

		dashboard.setCardFilters('chart-1', 'picker', [status])

		expect(dashboard.cardFiltersOn('chart-2')).toEqual([])
		expect(dashboard.cardIsFiltered('chart-2')).toBe(false)
	})

	it('is taken back whole by a reset, both controls at once', () => {
		const dashboard = newDashboard()

		dashboard.setCardFilters('chart-1', 'picker', [status])
		dashboard.setCardFilters('chart-1', 'row', [region])
		expect(dashboard.cardIsFiltered('chart-1')).toBe(true)

		dashboard.resetCardFilters('chart-1')

		expect(dashboard.cardFiltersOn('chart-1')).toEqual([])
		expect(dashboard.cardIsFiltered('chart-1')).toBe(false)
	})
})
