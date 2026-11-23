import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'

// the table list never answers, so the picker stays where it is while it waits
vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: () => new Promise(() => {}),
}))

import DataSourceTableList from './DataSourceTableList.vue'

async function picker() {
	const app = createSSRApp({
		render: () => h(DataSourceTableList as any, { data_source: 'Site DB' }),
	})
	app.component('FormControl', { render: () => h('input') })
	app.component('Button', { render: () => h('button') })
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe("the builder's table picker", () => {
	// @feature query.source-table
	it('says it is loading the tables until they arrive, and offers no sync', async () => {
		const html = await picker()

		expect(html).toContain('Loading tables…')
		expect(html).not.toContain('No Tables Found')
	})
})
