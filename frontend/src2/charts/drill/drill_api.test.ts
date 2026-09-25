import { describe, expect, it, vi } from 'vitest'
import { authoringDrillRows, fetchAuthoringDrillData } from './drill_api'

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

	// @feature dashboard.drill permissions.chart-run-as-owner
	it('names the saved dashboard its card sits on', async () => {
		// A caller who may not write the chart drills it as a reader. The server
		// checks a reader against the saved dashboard, never the grid sent.
		await fetchAuthoringDrillData(
			{ query: 'query-1', chart_type: 'Bar', config: {} as any },
			[],
			{
				chart: 'chart-1',
				dashboard: 'dashboard-1',
				items: [],
				filters: {},
				cardFilters: [],
			},
		)

		const [, args] = calls[calls.length - 1]
		expect(args.dashboard).toBe('dashboard-1')
	})

	// @feature permissions.chart-run-as-owner
	it('names the chart it is of where the surface is not a grid', async () => {
		// The chart's builder page has no filter context. The chart name tells the
		// server whose permissions filter the rows. Without it, the level runs as
		// the caller while the card runs as the owner.
		await fetchAuthoringDrillData(
			{ query: 'query-1', chart_type: 'Bar', config: {} as any },
			[],
			undefined,
			'chart-1',
		)

		const [, args] = calls[calls.length - 1]
		expect(args.chart_name).toBe('chart-1')
	})

	// @feature charts.drill-rows-reading charts.drill-rows-export permissions.chart-run-as-owner
	it('reads a builder rows level on the server, under the chart it is of', async () => {
		// Run as owner applies only on the server, where the pipeline is cut. So
		// every read of the level names the chart and goes to the server.
		const rows = authoringDrillRows(
			{ query: 'query-1', chart_type: 'Bar', config: {} as any },
			[{ segment_filters: [], action: { rows: true } }],
			undefined,
			'chart-1',
		)
		const reading = {
			row_filters: [],
			sort: [{ column: 'region', direction: 'desc' as const }],
			find: 'north',
			page: 2,
		}

		await rows.read(reading)
		const [read, readArgs] = calls[calls.length - 1]
		expect(read).toBe('insights.api.authoring.get_drill_data')
		expect(readArgs).toMatchObject({ chart_name: 'chart-1', ...reading })

		await rows.download(reading, 'csv')
		const [download, downloadArgs] = calls[calls.length - 1]
		expect(download).toBe('insights.api.authoring.download_drill_rows')
		expect(downloadArgs).toMatchObject({ chart_name: 'chart-1', find: 'north', format: 'csv' })
		expect(downloadArgs.page).toBeUndefined()
	})
})
