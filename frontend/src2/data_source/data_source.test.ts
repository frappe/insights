import { describe, expect, it, vi } from 'vitest'

const schemas = vi.hoisted(() => new Map<string, (schema: object) => void>())

vi.mock('frappe-ui', async () => ({
	...((await vi.importActual('frappe-ui')) as object),
	toast: { error: () => {} },
	call: (method: string, args: any) =>
		method === 'insights.api.data_sources.get_schema'
			? new Promise((resolve, reject) =>
					schemas.set(args.data_source, (schema) =>
						schema instanceof Error ? reject(schema) : resolve(schema),
					),
			  )
			: method === 'insights.api.data_sources.get_all_data_sources'
			  ? Promise.resolve([
						{ name: 'Site DB', title: 'Site DB', is_frappe_db: 1, is_site_db: 1 },
						{ name: 'warehouse', title: 'Warehouse', is_frappe_db: 0, is_site_db: 0 },
			    ])
			  : Promise.reject(new Error(method)),
}))

import { nextTick, ref } from 'vue'
import { tableLabel, useSourceSchema } from './data_source'

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

describe("a data source's schema", () => {
	// @feature query.native-sql-schema-explorer
	it('is loading until the source picked last answers, and an earlier answer is dropped', async () => {
		const source = ref('')
		const tables = useSourceSchema(source)
		expect(tables.loading).toBe(false)

		source.value = 'warehouse'
		await nextTick()
		expect(tables.loading).toBe(true)

		source.value = 'Site DB'
		await nextTick()
		schemas.get('Site DB')!({ tabToDo: { columns: [] } })
		schemas.get('warehouse')!({ orders: { columns: [] } })
		await vi.waitFor(() => expect(tables.loading).toBe(false))

		expect(Object.keys(tables.schema)).toEqual(['tabToDo'])
	})

	// @feature query.native-sql-schema-explorer
	it('says it failed, not that no source is picked, when the source does not answer', async () => {
		const source = ref('')
		const tables = useSourceSchema(source)
		source.value = 'unreachable'
		await nextTick()
		schemas.get('unreachable')!(new Error('timed out'))

		await vi.waitFor(() => expect(tables.failed).toBe(true))
		expect(tables.loading).toBe(false)
	})
})
