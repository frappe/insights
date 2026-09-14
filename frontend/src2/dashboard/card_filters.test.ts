import { describe, expect, it, vi } from 'vitest'
import type { Filter } from '../components/filter_picker/filter_picker'
import type { WorkbookDashboardItem } from '../types/workbook.types'

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

import useDashboard, { defaultFilterStates } from './dashboard'

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
	// @feature dashboard.filter-default
	it('seeds a filter with the default the author set, and an is_set default needs no value', () => {
		const filter = (filter_name: string, rest: any) =>
			({
				type: 'filter',
				filter_name,
				filter_type: 'String',
				links: {},
				...rest,
			}) as unknown as WorkbookDashboardItem

		expect(
			defaultFilterStates([
				filter('status', { default_operator: '=', default_value: 'canceled' }),
				filter('region', { default_operator: 'is_set' }),
				filter('seller', { default_operator: '=' }),
			]),
		).toEqual({
			status: { operator: '=', value: 'canceled' },
			// `is_set` asks about the column itself, so it says enough to run
			region: { operator: 'is_set', value: undefined },
		})
	})

	// @feature dashboard.card-filter
	it('is one card at a time', () => {
		const dashboard = newDashboard()

		dashboard.setCardFilters('chart-1', [status])

		expect(dashboard.cardFiltersOn('chart-2')).toEqual([])
		expect(dashboard.cardIsFiltered('chart-2')).toBe(false)
	})

	// @feature charts.reset-filters
	it('is taken back whole by a reset', () => {
		const dashboard = newDashboard()

		dashboard.setCardFilters('chart-1', [status, region])
		expect(dashboard.cardIsFiltered('chart-1')).toBe(true)

		dashboard.resetCardFilters('chart-1')

		expect(dashboard.cardFiltersOn('chart-1')).toEqual([])
		expect(dashboard.cardIsFiltered('chart-1')).toBe(false)
	})
})
