import type { Locator, Page } from '@playwright/test'
import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'
import {
	deleteUploadedTable,
	uploadCsvTable,
	uniqueTableName,
	uniqueTitle,
	UPLOADS_DATA_SOURCE,
} from '../helpers/insights'

/**
 * locator: <thead> uses <td>, and <tbody> ends with a cell-less spacer row, so
 * role=row over-counts. `:has(td)` keeps only real data rows.
 */
function dataRows(page: Page): Locator {
	return page.locator('tbody tr:has(td)')
}

function header(page: Page): Locator {
	return page.getByRole('banner')
}

/** Three rows, and no value in them appears anywhere else in the app. */
const CSV = ['region,order_count', 'Andromeda,12', 'Cassiopeia,34', 'Perseus,56'].join('\n')

test.describe('data-source', () => {
	test("a user browses a data source's table list and previews a table", async ({
		page,
		demoDataSource,
	}) => {
		await page.goto(`${INSIGHTS_PATH}/data-source/${demoDataSource}`)

		await expect(page.getByText('orders', { exact: true })).toBeVisible()
		await expect(page.getByText('customers', { exact: true })).toBeVisible()
		await expect(page.getByText('orderpayments', { exact: true })).toBeVisible()
		await expect(page.getByText('sellers', { exact: true })).toBeVisible()

		await page.getByText('sellers', { exact: true }).click()

		await expect(page).toHaveURL(new RegExp(`/data-source/${demoDataSource}/sellers$`))
		// A header cell proves the preview ran. <thead> uses <td>, so the role is
		// cell and not columnheader.
		await expect(page.getByRole('cell', { name: 'seller_city' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'SELL-0001' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'manaus' })).not.toHaveCount(0)
		// The preview reads the first 100 rows, and `sellers` holds 60.
		await expect(dataRows(page)).toHaveCount(60)
		await expect(page.getByText('Showing only the first 100 rows')).toBeVisible()
	})

	test('a user uploads a CSV and it becomes a queryable table', async ({
		page,
		adminApi,
		workbook,
	}) => {
		const table = uniqueTableName('upload')

		try {
			await page.goto(`${INSIGHTS_PATH}/data-source`)
			await header(page).getByRole('button', { name: 'New Data Source' }).click()
			await page.getByText('Upload CSV or Excel', { exact: true }).click()

			// locator: the file input is the one frappe-ui's FileUploader hides
			// behind its drop zone. It carries no label and no accessible name.
			await page.locator('input[type="file"]').setInputFiles({
				name: `${table}.csv`,
				mimeType: 'text/csv',
				buffer: Buffer.from(CSV),
			})

			// The dialog renames itself once it has read the file, and shows what
			// it read.
			const dialog = page.getByRole('dialog', { name: 'Import Table' })
			await expect(dialog.getByRole('cell', { name: 'Andromeda' })).toBeVisible()
			await expect(dialog.getByRole('cell', { name: 'order_count' })).toBeVisible()
			await expect(dialog.getByText('Showing 3 of 3 rows')).toBeVisible()

			await dialog.getByRole('button', { name: 'Import', exact: true }).click()

			await expect(page.getByText(`Table '${table}' imported successfully`)).toBeVisible()

			// The table is queryable when the query builder can start from it.
			await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)
			await page.getByText('Query Builder').click()
			// The dialog lists one sidebar item per Data Source, by title, and each
			// item is a clickable div with no role.
			await page.getByRole('navigation').getByText('Uploads', { exact: true }).click()
			await page.getByRole('button', { name: `${table} ${UPLOADS_DATA_SOURCE}` }).click()
			await page.getByRole('button', { name: 'Confirm' }).click()

			await expect(page.getByRole('cell', { name: 'region' })).toBeVisible()
			await expect(page.getByRole('cell', { name: 'Cassiopeia' })).toBeVisible()
			await expect(dataRows(page)).toHaveCount(3)
		} finally {
			await deleteUploadedTable(adminApi, {
				dataSource: UPLOADS_DATA_SOURCE,
				table,
				file: '',
			})
		}
	})

	test('a user connects a new database and the connection test reports', async ({ page }) => {
		const title = uniqueTitle('Data Source')

		await page.goto(`${INSIGHTS_PATH}/data-source`)
		await header(page).getByRole('button', { name: 'New Data Source' }).click()
		await page.getByText('MariaDB', { exact: true }).click()

		// A port on this machine that nothing listens on. The connection test
		// stays inside the host it runs on, and the refusal is immediate.
		const dialog = page.getByRole('dialog', { name: 'Connect to MariaDB' })
		await dialog.getByLabel('Title').fill(title)
		await dialog.getByLabel('Host').fill('127.0.0.1')
		await dialog.getByLabel('Port').fill('3999')
		await dialog.getByLabel('Database Name').fill('e2e_no_such_database')
		await dialog.getByLabel('Username').fill('e2e_no_such_user')
		await dialog.getByLabel('Password').fill('e2e-no-such-password')

		await dialog.getByRole('button', { name: 'Connect' }).click()

		await expect(dialog.getByRole('button', { name: 'Failed, Retry?' })).toBeVisible()
		await expect(page.getByText('Error', { exact: true })).toBeVisible()
		// A failed test blocks the data source, so the flow leaves nothing behind.
		await expect(dialog.getByRole('button', { name: 'Add Data Source' })).toBeDisabled()

		await dialog.getByRole('button', { name: 'Close' }).click()
		await page.getByPlaceholder('Search by Title').fill(title)
		await expect(page.getByText(title)).toHaveCount(0)
	})

	test('a user imports a table into the data store', async ({ page, adminApi }) => {
		// A Table Import runs on the `long` queue, and one bench worker serves
		// `short`, `default` and `long` in that order. The suite's own teardown
		// fills `default`, so the import waits for that backlog to drain. This is
		// the one flow in the suite that a deep queue delays rather than fails.
		test.setTimeout(180_000)

		const table = uniqueTableName('store')
		const uploaded = await uploadCsvTable(adminApi, table, CSV)

		try {
			await page.goto(`${INSIGHTS_PATH}/data-store`)
			await header(page).getByRole('button', { name: 'Import Table' }).click()

			const dialog = page.getByRole('dialog', { name: 'Import Table' })
			await dialog.getByRole('combobox', { name: 'Data Source' }).click()
			await page.getByRole('option', { name: 'Uploads' }).click()
			await dialog.getByRole('combobox', { name: 'Table' }).click()
			// An option carries the table name and the Data Source it belongs to.
			await page.getByRole('option', { name: `${table} ${UPLOADS_DATA_SOURCE}` }).click()

			await expect(dialog.getByText('Selected table has 3 rows.')).toBeVisible()
			await dialog.getByRole('button', { name: 'Import', exact: true }).click()
			await expect(dialog).toBeHidden()

			// A Table Import is a background job, and the list loads its rows once
			// when it mounts. The imported table therefore appears on a later load
			// of the screen, not on the one the import started from.
			await expect(async () => {
				await page.reload()
				await expect(page.getByText(table, { exact: true })).toBeVisible({
					timeout: 5_000,
				})
			}).toPass({ timeout: 150_000 })
			await expect(page.getByText(UPLOADS_DATA_SOURCE, { exact: true })).toBeVisible()
		} finally {
			await deleteUploadedTable(adminApi, uploaded)
		}
	})
})
