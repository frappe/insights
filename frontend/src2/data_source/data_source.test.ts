import { describe, expect, it, vi } from 'vitest'

vi.mock('frappe-ui', async () => ({
	...((await vi.importActual('frappe-ui')) as object),
	call: (method: string) =>
		method === 'insights.api.data_sources.get_all_data_sources'
			? Promise.resolve([
					{ name: 'Site DB', title: 'Site DB', is_frappe_db: 1, is_site_db: 1 },
					{ name: 'warehouse', title: 'Warehouse', is_frappe_db: 0, is_site_db: 0 },
			  ])
			: Promise.reject(new Error(method)),
}))

import { tableLabel } from './data_source'

describe('tableLabel', () => {
	// @feature query.source-table
	it('names a Frappe database table by its doctype, and any other table as it is', async () => {
		tableLabel({ data_source: 'Site DB', table_name: 'tabSales Invoice' })
		await new Promise((resolve) => setTimeout(resolve))

		expect(tableLabel({ data_source: 'Site DB', table_name: 'tabSales Invoice' })).toBe(
			'Sales Invoice',
		)
		expect(tableLabel({ data_source: 'warehouse', table_name: 'tabular_data' })).toBe(
			'tabular_data',
		)
	})
})
