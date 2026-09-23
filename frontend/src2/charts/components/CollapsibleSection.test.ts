import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { chartPreviewKey } from '../chart_preview'
import type { ChartRead } from '../chart_view'
import CollapsibleSection from './CollapsibleSection.vue'

// `ChartBuilder.vue` makes its form inert for a caller who may not write the
// chart, so no section can be opened by a click.

function section(can_write: boolean) {
	const app = createSSRApp({
		render: () => h(CollapsibleSection, { title: 'Limit', collapsed: true }, () => 'the limit'),
	})
	app.provide(chartPreviewKey, { doc: { can_write } } as unknown as ChartRead)
	return renderToString(app)
}

describe('a builder section that starts collapsed', () => {
	// @feature charts.preview permissions.chart-run-as-owner
	it('is open for a reader who may not write the chart', async () => {
		expect(await section(false)).toContain('the limit')
		expect(await section(true)).not.toContain('the limit')
	})
})
