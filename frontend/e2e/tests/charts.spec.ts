import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'

test.describe('charts', () => {
	test('a user creates a Bar chart with one dimension and one measure', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		// locator: the sidebar's two add buttons are icon-only frappe-ui Buttons
		// with no accessible name. `svg.lucide-plus` is the "+" icon; the new
		// folder icon beside it carries `lucide-folder-plus` instead.
		await page
			.locator('div.mb-1:has(div:text-is("Charts")) button:has(svg.lucide-plus)')
			.click()

		await page.getByRole('button', { name: 'Bar', exact: true }).click()

		// locator: X Axis and Y Axis are collapsible sections holding buttons with
		// the same name. The section's own heading button is what tells them apart.
		const xAxis = page.locator('div.flex.flex-col:has(> button > div > p:text-is("X Axis"))')
		await xAxis.getByRole('button', { name: 'Select a column' }).click()
		await page.getByRole('option', { name: 'order_status' }).click()

		const yAxis = page.locator('div.flex.flex-col:has(> button > div > p:text-is("Y Axis"))')
		await yAxis.getByRole('button', { name: 'Select a column' }).click()
		// "Unique Count of..." holds the same words, so match the whole string.
		await page.getByText('Count of...', { exact: true }).click()
		const measureDialog = page.getByRole('dialog', { name: 'Select a column' })
		await measureDialog.getByText('order_id', { exact: true }).click()

		// locator: echarts writes `_echarts_instance_` on the element it renders
		// into, so this names the chart and nothing else on the page. The result
		// preview under the chart repeats every label, and an unscoped getByText
		// would reach both.
		const chart = page.locator('[_echarts_instance_]')

		// The chart renders as SVG, so a category label is a real <text> node.
		// Category order changes between runs, so nothing here depends on it.
		await expect(chart.getByText('delivered')).toBeVisible()
		await expect(chart.getByText('canceled')).toBeVisible()
		// The measure is the count of orders, and 1,778 of the 2,000 are
		// delivered, so the value axis runs to a 1.8K tick.
		await expect(chart.getByText('1.8K')).toBeVisible()
	})
})
