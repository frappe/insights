import { beforeEach, describe, expect, it, vi } from 'vitest'

const calls = vi.hoisted(() => [] as string[])

vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: (method: string) => {
		calls.push(method)
		return Promise.resolve(false)
	},
}))

import { pastedWorkbook } from './workbook_file'

beforeEach(() => {
	calls.length = 0
})

// The paste handler on `WorkbookList.vue` hands this whatever the clipboard
// holds when a user presses Cmd+V on the workbook list.

describe('a paste on the workbook list', () => {
	// @feature workbook.copy-paste
	it('sends nothing to the server that is not a JSON object', async () => {
		expect(await pastedWorkbook('hunter2')).toBeUndefined()
		expect(await pastedWorkbook('["a", "b"]')).toBeUndefined()
		expect(await pastedWorkbook('42')).toBeUndefined()
		expect(calls).toEqual([])
	})
})
