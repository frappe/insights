import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import DataTable from './DataTable.vue'

async function grid(props: Record<string, any>) {
	const app = createSSRApp({ render: () => h(DataTable as any, props) })
	app.config.warnHandler = () => {}
	return (await renderToString(app)).replace(/<!--[\s\S]*?-->/g, '')
}

const columns = [
	{ name: 'customer', type: 'String' },
	{ name: 'Overdue', type: 'Decimal' },
]
const rows = [
	{ customer: 'Agra Builders', Overdue: null },
	{ customer: null, Overdue: 28367 },
]

describe('a result grid over missing values', () => {
	// @feature query.result-blanks
	it('leaves a missing number blank, as it leaves missing text', async () => {
		const html = await grid({ columns, rows })

		expect(html).toContain('Agra Builders')
		expect(html).not.toMatch(/>\s*null\s*</)
	})
})
