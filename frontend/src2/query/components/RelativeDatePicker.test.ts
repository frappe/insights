import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import RelativeDatePicker from './RelativeDatePicker.vue'

// On open, the picker reads the stored span into its three controls and writes
// it back, so opening is already a round trip. The server must accept what it
// writes. `parse_span` refuses any other string, and then every card the filter
// reaches fails with that string in its error.

async function opensOn(stored: string) {
	let written = stored
	const app = createSSRApp({
		render: () =>
			h(RelativeDatePicker, {
				modelValue: stored,
				'onUpdate:modelValue': (value: string) => (written = value),
			}),
	})
	// The app registers frappe-ui components globally. This test does not, so it
	// silences the warnings for unresolved components.
	app.config.warnHandler = () => {}
	await renderToString(app)
	return written
}

describe('a relative date the picker opens on', () => {
	// @feature query.filter-relative-date
	it('keeps the span it was stored as, counted or not', async () => {
		// the server reads a span with no count as one period
		expect(await opensOn('Last Month')).toBe('Last 1 Month')
		expect(await opensOn('Next Quarter')).toBe('Next 1 Quarter')

		expect(await opensOn('Last 3 Month')).toBe('Last 3 Month')
		expect(await opensOn('Current Year')).toBe('Current Year')
		expect(await opensOn('Last 2 Week (include current)')).toBe('Last 2 Week (include current)')
		// a Fiscal Year span has no "(include current)" option
		expect(await opensOn('Last 1 Fiscal Year')).toBe('Last 1 Fiscal Year')
	})

	// @feature query.filter-relative-date
	it('leaves a span it has no control for as it stands', async () => {
		// The picker has no option for `<unit> to date`. Opening the picker must not
		// change the stored value, whatever the three controls show.
		expect(await opensOn('month to date')).toBe('month to date')
		expect(await opensOn('fiscal year to date')).toBe('fiscal year to date')
	})
})
