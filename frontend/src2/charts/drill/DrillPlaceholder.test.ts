import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import type { ChartFailure } from '../adapter/types'
import DrillPlaceholder from './DrillPlaceholder.vue'

function placeholder(failure: ChartFailure) {
	const app = createSSRApp({
		render: () => h(DrillPlaceholder, { loading: false, failure }),
	})
	// The app registers frappe-ui components globally. This test does not, so it
	// silences the warnings for unresolved components.
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('a drill level that renders nothing', () => {
	// @feature permissions.not-permitted-chart
	it('names what a refused level needs and shows no retry', async () => {
		const html = await placeholder({
			kind: 'notPermitted',
			headline: 'Not Permitted',
			detailText: 'Needs read access to Sales Invoice',
		})

		expect(html).toContain('Not Permitted')
		expect(html).toContain('Needs read access to Sales Invoice')
		// the reader cannot change their grants, so a retry is refused the same way
		expect(html).not.toContain('Retry')
	})

	// @feature charts.retry
	it('shows a retry for a level that failed', async () => {
		const html = await placeholder({
			headline: 'This drill is not available',
		})

		expect(html).toContain('This drill is not available')
		expect(html).toContain('Retry')
	})
})
