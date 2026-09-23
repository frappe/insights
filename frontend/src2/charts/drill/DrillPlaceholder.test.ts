import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import type { ChartFailure } from '../adapter/types'
import DrillPlaceholder from './DrillPlaceholder.vue'

// What the drill draws where the level would be. A level that would not load
// and a level the reader may not read are two different answers: one is worth
// asking again and the other never will be.

function placeholder(failure: ChartFailure) {
	const app = createSSRApp({
		render: () => h(DrillPlaceholder, { loading: false, failure }),
	})
	// the app registers frappe-ui's components globally; this render is one
	// placeholder and does not need them resolved
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('a drill level that draws nothing', () => {
	// @feature permissions.not-permitted-chart
	it('names what a refused level needs and offers no retry', async () => {
		const html = await placeholder({
			kind: 'notPermitted',
			headline: 'Not Permitted',
			detailText: 'Needs read access to Sales Invoice',
		})

		expect(html).toContain('Not Permitted')
		expect(html).toContain('Needs read access to Sales Invoice')
		// nothing ran, the reader owns no grant they could change, and asking
		// again would be refused the same way
		expect(html).not.toContain('Retry')
	})

	// @feature charts.retry
	it('offers a retry for a level that failed', async () => {
		const html = await placeholder({
			headline: 'This drill is not available',
		})

		expect(html).toContain('This drill is not available')
		expect(html).toContain('Retry')
	})
})
