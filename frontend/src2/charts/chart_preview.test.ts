import { beforeEach, describe, expect, it, vi } from 'vitest'
import { waitUntil } from '../helpers'
import useQuery from '../query/query'
import useChartPreview from './chart_preview'

const calls = vi.hoisted(() => [] as string[])

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: (method: string, args: any) => {
		calls.push(method)
		if (method === 'insights.api.get_doc') {
			return Promise.resolve({
				doctype: 'Insights Query v3',
				name: args.name,
				operations: [],
				modified: '2026-09-21 10:00:00',
			})
		}
		return Promise.resolve({ columns: [], rows: [] })
	},
}))

beforeEach(() => {
	calls.length = 0
})

describe('a card drawing a chart in the builder', () => {
	// @feature dashboard.card-follows-edits
	it('is asked again once the query it reads is saved', async () => {
		const query = useQuery('query-1')
		await waitUntil(() => query.isloaded)
		const chart = {
			doc: { name: 'chart-1', chart_type: 'Bar', query: 'query-1', config: { limit: 100 } },
		}
		const preview = useChartPreview(chart as any)
		const runs = () => calls.filter((method) => method.endsWith('get_chart_data')).length

		await preview.load()
		await preview.load()
		expect(runs()).toBe(1)

		query.doc.modified = '2026-09-21 10:05:00'
		await preview.load()
		expect(runs()).toBe(2)
	})

	// @feature dashboard.card-follows-edits
	it('does not load a query only to ask whether it was saved', async () => {
		const chart = {
			doc: { name: 'chart-2', chart_type: 'Bar', query: 'query-2', config: { limit: 100 } },
		}
		const preview = useChartPreview(chart as any)

		await preview.load()

		expect(calls.filter((method) => method === 'insights.api.get_doc')).toEqual([])
	})
})
