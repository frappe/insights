import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'

test.describe('query', () => {
	test('a user picks a table as a query source and sees rows', async ({
		page,
		demoDataSource,
		workbook,
	}) => {
		// Opening a Workbook with no Query creates one and routes to it, so the
		// interface picker is the first thing on screen.
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)

		// The three interface cards are clickable divs with no role and no label,
		// so getByText is the first rung of the ladder that reaches them.
		await page.getByText('Query Builder').click()

		await page.getByRole('button', { name: `orders ${demoDataSource}` }).click()
		await page.getByRole('button', { name: 'Confirm' }).click()

		// A column header proves the source ran. <thead> uses <td>, so the role is
		// cell and not columnheader.
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'ORD-00001' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'delivered' })).not.toHaveCount(0)

		// locator: <thead> uses <td>, and <tbody> ends with a cell-less spacer row,
		// so role=row over-counts. `:has(td)` keeps only real data rows. The editor
		// shows one page of 100 rows out of the 2,000 in the table.
		await expect(page.locator('tbody tr:has(td)')).toHaveCount(100)
	})
})
