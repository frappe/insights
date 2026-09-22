import { describe, expect, it, vi } from 'vitest'
import { waitUntil } from './index'
import useDocumentResource from './resource'

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	toast: { error: () => {} },
	call: () => Promise.reject(new Error('Insights Chart v3 chart-1 not found')),
}))

describe('a document the server will not hand over', () => {
	// @feature shared.missing-link
	it('is marked failed', async () => {
		const chart = useDocumentResource('Insights Chart v3', 'chart-1', {
			initialDoc: { doctype: 'Insights Chart v3', name: 'chart-1', owner: '' },
		})

		await waitUntil(() => !chart.loading)

		expect(chart.failed).toBe(true)
	})
})
