import { describe, expect, it, vi } from 'vitest'
import { fetchAuthoringDrillData } from './drill_api'

// The wire contract, asserted where it is written. A drill level has to be
// narrowed by everything the card itself was narrowed by — the grid's filters
// and the reader's own card filter — or the breakdown counts rows the card does
// not draw.

const calls: [string, Record<string, any>][] = []
vi.mock('frappe-ui', () => ({
	call: (method: string, args: Record<string, any>) => {
		calls.push([method, args])
		return Promise.resolve({})
	},
}))

describe('a drill level', () => {
	// @feature dashboard.card-filter
	it('carries the card filter the read runs under', async () => {
		await fetchAuthoringDrillData(
			{ query: 'query-1', chart_type: 'Bar', config: {} as any },
			[
				{
					segment_filters: [{ column: 'region', operator: '=', value: 'north' }],
					action: { breakdown: 'category' },
				},
			],
			{
				chart: 'chart-1',
				items: [],
				filters: {},
				cardFilters: [{ column: 'city', operator: '=', value: 'delhi' }],
			},
		)

		const [method, args] = calls[calls.length - 1]
		expect(method).toBe('insights.api.authoring.get_drill_data')
		expect(args.chart_name).toBe('chart-1')
		expect(args.card_filters).toEqual([{ column: 'city', operator: '=', value: 'delhi' }])
	})

	// @feature dashboard.card-filter
	it('names no card filter where the surface holds none', async () => {
		await fetchAuthoringDrillData({ query: 'query-1', operations: [] }, [])

		const [, args] = calls[calls.length - 1]
		expect(args.card_filters).toBeUndefined()
	})
})
