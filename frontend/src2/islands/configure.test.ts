import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { usePagination } from '../composables/usePagination'
import DataTableFooter from '../components/DataTableFooter.vue'
import { configureIsland } from './configure'

/** Desk's `SetVueGlobals`: sets `__` to `frappe._` on every app. */
function deskGlobals(app: any) {
	app.config.globalProperties.__ = (text: string, replace: any) =>
		replace && typeof replace === 'object'
			? text.replace(/\{(\d+)\}/g, (match, index) => replace[index] ?? match)
			: text
}

function footerOnPage(page: number) {
	const pagination = usePagination({
		rowCount: 100,
		pageSize: 100,
		totalRowCount: 1240,
		currentPage: page,
		onPageChange: () => {},
		enabled: true,
	})
	const app = createSSRApp({ render: () => h(DataTableFooter, { pagination }) })
	deskGlobals(app)
	configureIsland(app)
	return renderToString(app)
}

describe('an island mounted on a desk page', () => {
	// @feature settings.translations
	it('formats a string that names its arguments by position', async () => {
		expect(await footerOnPage(2)).toContain('Page 2')
	})
})
