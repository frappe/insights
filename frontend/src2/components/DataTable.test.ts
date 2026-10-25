import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import session from '../session'
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

describe('the row totals column', () => {
	const amounts = [
		{ name: 'Revenue', type: 'Decimal' },
		{ name: 'Outstanding', type: 'Decimal' },
	]
	const formats = { Revenue: 'currency', Outstanding: 'currency' }

	// @feature charts.table-totals
	it('is headed Total and prints in the unit its columns share', async () => {
		session.site.currency = 'INR'
		session.site.currency_symbols = {
			INR: { symbol: '₹', symbol_on_right: false, number_format: '#,###.##' },
		}
		const html = await grid({
			columns: amounts,
			rows: [{ Revenue: 100, Outstanding: 20 }],
			columnFormats: formats,
			showRowTotals: true,
		})
		session.site.currency = null
		session.site.currency_symbols = {}

		expect(html).toMatch(/>\s*Total\s*</)
		expect(html).toContain('₹ 120.00')
	})

	// @feature charts.table-totals
	it('prints bare over columns in different units', async () => {
		const html = await grid({
			columns: amounts,
			rows: [{ Revenue: 100, Outstanding: 20 }],
			columnFormats: { Revenue: 'percent' },
			showRowTotals: true,
		})

		expect(html).toMatch(/>\s*120\s*</)
	})

	// @feature charts.table-totals
	it('keeps a total and its currency on one line, under a whole header', async () => {
		const html = await grid({
			columns: amounts,
			rows: [{ Revenue: 100, Outstanding: 20 }],
			columnFormats: formats,
			showRowTotals: true,
		})

		const header = html.match(/<td[^>]*>\s*<div[^>]*>\s*Total\s*<\/div>/)![0]
		expect(header).not.toContain('truncate')
		expect(header).toContain('whitespace-nowrap')
		const total = html.match(/<td[^>]*>[^<]*120[^<]*<\/td>/)![0]
		expect(total).toContain('whitespace-nowrap')
	})
})
