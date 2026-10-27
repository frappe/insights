import { describe, expect, it } from 'vitest'
import { computed, createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ResultStatus from './ResultStatus.vue'

const firstPage = {
	from: computed(() => 1),
	to: computed(() => 100),
	isLastPage: computed(() => false),
} as any

async function statusLine(props: Record<string, any>) {
	const app = createSSRApp({ render: () => h(ResultStatus as any, props) })
	app.config.warnHandler = () => {}
	return (await renderToString(app)).replace(/<!--[\s\S]*?-->/g, '')
}

describe('the row count of a result longer than a page', () => {
	// @feature query.row-count
	it('offers to load the count in words, not behind an icon in the sentence', async () => {
		const html = await statusLine({
			paging: firstPage,
			loadedCount: 100,
			onFetchCount: () => {},
		})

		expect(html).toContain('Showing 1–100')
		expect(html).not.toMatch(/Showing 1–100 of\s*</)
		expect(html).toMatch(/>\s*Load Count\s*</)
	})

	// @feature query.row-count
	it('states the count once it is known', async () => {
		const html = await statusLine({
			paging: firstPage,
			loadedCount: 100,
			totalRowCount: 2500,
			onFetchCount: () => {},
		})

		expect(html).toContain('Showing 1–100 of 2,500 rows')
		expect(html).not.toContain('Load Count')
	})
})
