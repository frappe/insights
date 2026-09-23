import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

// What a refused write leaves behind. The document is autosaved, so a value the
// server will not take has to come off it: left on, the watcher re-sends the
// same refused payload on every later edit and nothing the author types after
// that point ever reaches the server.

const answers: { update?: (args: any) => Promise<any> } = {}

vi.mock('frappe-ui', async () => ({
	...((await vi.importActual('frappe-ui')) as object),
	call: (method: string, args: any) => {
		if (method === 'insights.api.get_doc') {
			return Promise.resolve({
				doctype: 'Insights Chart v3',
				name: 'chart-1',
				owner: 'alice@test.com',
				title: 'Sales',
				visibility: 'Private',
			})
		}
		if (method === 'frappe.client.set_value') {
			return answers.update!(args)
		}
		return Promise.resolve({})
	},
	toast: { error: () => {} },
}))

import useDocumentResource from './resource'

async function settled() {
	for (let i = 0; i < 12; i++) await nextTick()
}

/** A write the server read and refused, as `frappeRequest` rejects with it. */
function refusal(exc_type = 'PermissionError', status = 403) {
	return Object.assign(new Error('You do not have permission'), { exc_type, status })
}

/** A write that never reached the server: offline, aborted, a bench restarting. */
function transportFailure() {
	return new TypeError('Failed to fetch')
}

/**
 * A chart as `chart.ts` `getChartResource` opens it: autosaved, no local draft.
 * The share dialog writes `visibility` on it.
 */
async function autosavedChart() {
	const chart = useDocumentResource<any>('Insights Chart v3', 'chart-1', {
		initialDoc: { doctype: 'Insights Chart v3', name: 'chart-1', owner: '' },
		enableAutoSave: true,
		disableLocalStorage: true,
	})
	await settled()
	return chart
}

describe('a document the server refuses', () => {
	// @feature permissions.visibility
	it('takes back the refused value and keeps what the author typed since', async () => {
		let refuse!: (error: Error) => void
		answers.update = () => new Promise((_, reject) => (refuse = reject))
		const chart = await autosavedChart()

		chart.doc.visibility = 'Public'
		const saving = chart.save()
		await settled()
		// typed while the write was in flight: the refused write never carried it
		chart.doc.title = 'Sales — Q4 rework'
		refuse(refusal())
		await expect(saving).rejects.toThrow()
		await settled()

		// the refused level is off the document, so the next write is not the
		// same refused payload again
		expect(chart.doc.visibility).toBe('Private')
		expect(chart.doc.title).toBe('Sales — Q4 rework')
		expect(chart.isdirty).toBe(true)
	})

	// @feature workbook.save
	it('keeps every edit when the write never reached the server', async () => {
		answers.update = () => Promise.reject(transportFailure())
		const chart = await autosavedChart()

		chart.doc.title = 'Sales — Q4 rework'
		await expect(chart.save()).rejects.toThrow()
		await settled()

		// still dirty, so the next autosave sends it again
		expect(chart.doc.title).toBe('Sales — Q4 rework')
		expect(chart.isdirty).toBe(true)
	})

	// @feature alerts.condition
	it('keeps every edit on a document its author saves by hand', async () => {
		// `alert.ts` opens an alert without autosave; `InsightsAlert.validate`
		// refuses an invalid condition with a ValidationError
		answers.update = () => Promise.reject(refusal('ValidationError', 417))
		const alert = useDocumentResource<any>('Insights Alert', 'alert-1', {
			initialDoc: { doctype: 'Insights Alert', name: 'alert-1', owner: '' },
			enableAutoSave: false,
			disableLocalStorage: true,
		})
		await settled()

		alert.doc.title = 'Sales dropped'
		await expect(alert.save()).rejects.toThrow()
		await settled()

		expect(alert.doc.title).toBe('Sales dropped')
		expect(alert.isdirty).toBe(true)
	})
})
