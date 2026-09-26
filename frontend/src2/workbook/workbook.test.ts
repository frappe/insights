import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

// The server refuses to delete an item a desk document links to. The row stays
// in the sidebar, the author stays on the same page, and a toast shows the error.

const deletes: { answer: () => Promise<any> } = { answer: () => Promise.resolve({}) }
const errors: string[] = []

vi.mock('frappe-ui', async () => ({
	...((await vi.importActual('frappe-ui')) as object),
	call: (method: string, args: any) => {
		if (method === 'insights.api.get_doc') {
			if (args.doctype === 'Insights Workbook') {
				return Promise.resolve({
					doctype: 'Insights Workbook',
					name: 'wb-1',
					owner: 'alice@test.com',
					title: 'Sales',
					folders: '[]',
					queries: JSON.stringify([{ name: 'q-1' }, { name: 'q-2' }]),
					charts: JSON.stringify([{ name: 'c-1' }, { name: 'c-2' }]),
					dashboards: JSON.stringify([{ name: 'd-1' }, { name: 'd-2' }]),
				})
			}
			return Promise.resolve({ doctype: args.doctype, name: args.name, owner: '' })
		}
		if (method === 'frappe.client.delete') return deletes.answer()
		return Promise.resolve({})
	},
	toast: { error: (message: string) => errors.push(message), success: () => {} },
}))

// Confirms at once and catches a rejected promise, as `ConfirmDialog` does.
vi.mock('../helpers/confirm_dialog', () => ({
	confirmDialog: ({ onSuccess }: { onSuccess: () => any }) => onSuccess()?.catch?.(() => {}),
}))

const replace = vi.fn()
vi.mock('../router', () => ({
	default: {
		replace: (path: string) => replace(path),
		currentRoute: { value: { path: '' } },
		options: { history: { state: { back: '/workbook' } } },
	},
}))

import useWorkbook from './workbook'

async function settled() {
	for (let i = 0; i < 20; i++) await nextTick()
	await new Promise((resolve) => setTimeout(resolve))
}

function linkedFromDesk() {
	return Object.assign(new Error('Cannot delete: it is linked with Dashboard Chart Sales'), {
		exc_type: 'LinkExistsError',
		status: 417,
	})
}

async function openWorkbook() {
	const workbook = useWorkbook('wb-1')
	await workbook.load()
	await settled()
	replace.mockClear()
	errors.length = 0
	return workbook
}

describe('removing an item from the sidebar', () => {
	beforeEach(() => {
		deletes.answer = () => Promise.resolve({})
	})

	const removals = [
		['query', 'queries', 'removeQuery', 'q-1'],
		['chart', 'charts', 'removeChart', 'c-1'],
		['dashboard', 'dashboards', 'removeDashboard', 'd-1'],
	] as const

	for (const [type, rows, remove, name] of removals) {
		// @feature workbook.remove-item
		it(`keeps a ${type} the server refuses to delete, and stays on it`, async () => {
			const workbook = await openWorkbook()
			deletes.answer = () => Promise.reject(linkedFromDesk())

			workbook[remove](name)
			await settled()

			expect(workbook.doc[rows].map((row) => row.name)).toContain(name)
			expect(replace).not.toHaveBeenCalled()
			expect(errors).toHaveLength(1)
		})

		// @feature workbook.remove-item
		it(`takes a deleted ${type} off the sidebar and opens the next one`, async () => {
			const workbook = await openWorkbook()

			workbook[remove](name)
			await settled()

			expect(workbook.doc[rows].map((row) => row.name)).not.toContain(name)
			expect(replace).toHaveBeenCalledWith(`/workbook/wb-1/${type}/${name.replace('1', '2')}`)
		})
	}
})

describe('deleting the workbook', () => {
	// @feature workbook.delete
	it('stays on a workbook the server refuses to delete', async () => {
		const workbook = await openWorkbook()
		deletes.answer = () => Promise.reject(linkedFromDesk())

		workbook.delete()
		await settled()

		expect(replace).not.toHaveBeenCalled()
		expect(errors).toHaveLength(1)
	})
})
