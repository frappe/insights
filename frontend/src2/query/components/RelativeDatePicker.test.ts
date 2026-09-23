import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import RelativeDatePicker from './RelativeDatePicker.vue'

// The picker reads a stored span into its three controls and writes the span
// back, so opening it is already a round trip. What it writes has to be a span
// the server runs: `parse_span` refuses anything else and every card the filter
// reaches fails with the string in the message.

/** The span the picker writes back when it opens on `stored`. */
async function opensOn(stored: string) {
	let written = stored
	const app = createSSRApp({
		render: () =>
			h(RelativeDatePicker, {
				modelValue: stored,
				'onUpdate:modelValue': (value: string) => (written = value),
			}),
	})
	// the app registers frappe-ui's components globally; this render is one
	// component and does not need them resolved
	app.config.warnHandler = () => {}
	await renderToString(app)
	return written
}

describe('a relative date the picker opens on', () => {
	// @feature query.filter-relative-date
	it('keeps the span it was stored as, counted or not', async () => {
		// a span that names no count covers one period, which is what the server
		// reads it as
		expect(await opensOn('Last Month')).toBe('Last 1 Month')
		expect(await opensOn('Next Quarter')).toBe('Next 1 Quarter')

		expect(await opensOn('Last 3 Month')).toBe('Last 3 Month')
		expect(await opensOn('Current Year')).toBe('Current Year')
		expect(await opensOn('Last 2 Week (include current)')).toBe('Last 2 Week (include current)')
		// a fiscal year has no current period to take in
		expect(await opensOn('Last 1 Fiscal Year')).toBe('Last 1 Fiscal Year')
	})

	// @feature query.filter-relative-date
	it('leaves a span it has no control for as it stands', async () => {
		// `<unit> to date` is the grammar's fourth shape and the picker offers no
		// option for it. Opening the editor is not editing: the stored default is
		// still the month so far, whatever the three controls happen to show.
		expect(await opensOn('month to date')).toBe('month to date')
		expect(await opensOn('fiscal year to date')).toBe('fiscal year to date')
	})
})
