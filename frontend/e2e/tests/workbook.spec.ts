import type { Locator, Page } from '@playwright/test'
import { expect, test } from '../fixtures'
import { INSIGHTS_PATH, VIEWER_EMAIL } from '../helpers/auth'
import { deleteWorkbook } from '../helpers/insights'

/**
 * locator: the workbook navbar has no landmark role, and its title is a
 * contenteditable div that Chromium exposes as plain text. Its height class is
 * the only handle, and it is unique on the workbook screen.
 */
function navbar(page: Page): Locator {
	return page.locator('div.h-11')
}

function workbookTitle(page: Page): Locator {
	return navbar(page).locator('.contenteditable')
}

/**
 * locator: the workbook actions menu opens from an icon-only button that
 * carries no accessible name. `aria-haspopup` marks it as the only menu trigger
 * in the navbar.
 */
function actionsMenu(page: Page): Locator {
	return navbar(page).locator('button[aria-haspopup="menu"]')
}

/**
 * The Share button hides while the workbook holds unsaved changes, so a user
 * reads its return as "the workbook is saved". Assert it goes away first,
 * because it is already on screen when the edit starts.
 */
async function expectSaved(page: Page) {
	const share = navbar(page).getByRole('button', { name: 'Share' })
	await expect(share).toBeHidden()
	await expect(share).toBeVisible()
}

/** Drag a sidebar item onto a folder row. Sortable.js needs real mouse moves. */
async function dragOnto(page: Page, item: Locator, target: Locator) {
	const from = await item.boundingBox()
	const to = await target.boundingBox()
	await page.mouse.move(from!.x + from!.width / 2, from!.y + from!.height / 2)
	await page.mouse.down()
	await page.mouse.move(to!.x + to!.width / 2, to!.y + to!.height / 2, { steps: 20 })
	await page.mouse.move(to!.x + to!.width / 2, to!.y + to!.height / 2 + 2)
	await page.mouse.up()
}

test.describe('workbook', () => {
	test('a user creates a workbook from the list', async ({ page, adminApi }) => {
		await page.goto(`${INSIGHTS_PATH}/workbook`)
		await page.getByRole('button', { name: 'New Workbook' }).click()

		// A new workbook redirects to the query the app creates for it.
		await page.waitForURL(/\/workbook\/\d+\/query\//)
		const name = page.url().match(/\/workbook\/(\d+)\//)![1]
		// A workbook with no title is named after itself.
		await expect(workbookTitle(page)).toHaveText(`Workbook ${name}`)
		await expect(page.getByRole('link', { name: 'Query 1' })).toBeVisible()
		await expectSaved(page)

		// The logo returns to the list without reloading the app.
		await page.getByRole('link', { name: 'logo' }).click()
		await page.getByPlaceholder('Search by title').fill(`Workbook ${name}`)
		await expect(page.getByText(`Workbook ${name}`)).toBeVisible()

		await deleteWorkbook(adminApi, name)
	})

	test('a user opens a workbook and switches query, chart, dashboard tabs', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, query, chart, dashboard } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)

		// A workbook opens on its first query.
		await expect(page).toHaveURL(new RegExp(`/workbook/${workbook.name}/query/${query.name}$`))
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'delivered' })).not.toHaveCount(0)

		// locator: echarts writes `_echarts_instance_` on the element it renders
		// into, so this names the chart and nothing else on the page.
		const rendered = page.locator('[_echarts_instance_]')

		await page.getByRole('link', { name: chart.title }).click()
		await expect(page).toHaveURL(new RegExp(`/workbook/${workbook.name}/chart/${chart.name}$`))
		await expect(rendered.getByText('delivered')).toBeVisible()

		await page.getByRole('link', { name: dashboard.title }).click()
		await expect(page).toHaveURL(
			new RegExp(`/workbook/${workbook.name}/dashboard/${dashboard.name}$`),
		)
		// The dashboard draws the chart narrower, and echarts drops the category
		// labels that no longer fit. The value axis still runs to a 1.8K tick,
		// because 1,778 of the 2,000 orders are delivered.
		await expect(rendered.getByText('1.8K')).toBeVisible()
		await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible()
	})

	test('a user renames a workbook', async ({ page, workbook }) => {
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)
		const title = workbookTitle(page)
		await expect(title).toHaveText(workbook.title)

		const renamed = `${workbook.title} renamed`
		await title.click()
		await page.keyboard.press('ControlOrMeta+a')
		await page.keyboard.type(renamed)
		await page.keyboard.press('Enter')

		await expect(title).toHaveText(renamed)
		await expectSaved(page)

		await page.getByRole('link', { name: 'logo' }).click()
		await page.getByPlaceholder('Search by title').fill(renamed)
		await expect(page.getByText(renamed)).toBeVisible()
		await expect(page.getByText(workbook.title, { exact: true })).toHaveCount(0)
	})

	test('a workbook saves and survives a reload', async ({ page, workbook }) => {
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)
		await expect(page.getByRole('link', { name: 'Query 1' })).toBeVisible()

		await page.getByRole('button', { name: 'Add Dashboards' }).click()
		await expect(page.getByRole('link', { name: 'Dashboard 1' })).toBeVisible()
		await expect(page).toHaveURL(new RegExp(`/workbook/${workbook.name}/dashboard/`))
		await expectSaved(page)

		await page.reload()

		await expect(workbookTitle(page)).toHaveText(workbook.title)
		await expect(page.getByRole('link', { name: 'Query 1' })).toBeVisible()
		await expect(page.getByRole('link', { name: 'Dashboard 1' })).toBeVisible()
		await expect(page).toHaveURL(new RegExp(`/workbook/${workbook.name}/dashboard/`))
	})

	test('a user deletes a workbook', async ({ page, workbook }) => {
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)
		await expect(workbookTitle(page)).toHaveText(workbook.title)

		await actionsMenu(page).click()
		await page.getByRole('menuitem', { name: 'Delete' }).click()
		const confirm = page.getByRole('dialog', { name: 'Delete Workbook' })
		await expect(
			confirm.getByText('Are you sure you want to delete this workbook?'),
		).toBeVisible()
		await confirm.getByRole('button', { name: 'Confirm' }).click()

		// Deleting returns the user to the list, without the deleted workbook.
		await expect(page).toHaveURL(new RegExp(`${INSIGHTS_PATH}/workbook$`))
		await page.getByPlaceholder('Search by title').fill(workbook.title)
		await expect(page.getByText(workbook.title, { exact: true })).toHaveCount(0)
		await expect(page.getByText('No Workbooks')).not.toHaveCount(0)
	})

	test('a user creates a folder and moves a query into it', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)
		const item = page.getByRole('link', { name: query.title })
		await expect(item).toBeVisible()

		await page.getByRole('button', { name: 'New folder in Queries' }).click()
		// locator: a folder row is a div with no role. Its own class is what the
		// drop-target styling hangs off, so it is the stable handle.
		const folder = page.locator('.folder-header').filter({ hasText: 'Untitled' })
		await expect(folder).toBeVisible()

		await dragOnto(page, item, folder)

		// A new folder is collapsed, so a query inside it leaves the sidebar.
		await expect(item).toBeHidden()
		await folder.click()
		await expect(item).toBeVisible()

		await page.reload()
		await expect(folder).toBeVisible()
		await expect(item).toBeHidden()
	})

	test('a user shares a workbook with another user', async ({ page, viewerPage, workbook }) => {
		await viewerPage.goto(`${INSIGHTS_PATH}/workbook`)
		await expect(viewerPage.getByText(workbook.title)).toHaveCount(0)

		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)
		await navbar(page).getByRole('button', { name: 'Share' }).click()

		const dialog = page.getByRole('dialog', { name: 'Manage Workbook Access' })
		await expect(dialog.getByText('Only you have access to this workbook')).not.toHaveCount(0)
		await dialog.getByRole('combobox', { name: 'Search by name or email' }).click()
		await dialog.getByRole('combobox', { name: 'Search by name or email' }).fill(VIEWER_EMAIL)
		await page.getByRole('option', { name: 'E2E Viewer' }).click()
		await dialog.getByRole('button', { name: 'Share', exact: true }).click()

		await expect(dialog.getByText(VIEWER_EMAIL)).toBeVisible()
		await expect(dialog.getByRole('button', { name: 'Can View' })).toBeVisible()
		await dialog.getByRole('button', { name: 'Save' }).click()
		await expect(page.getByText('Permissions updated')).toBeVisible()

		await viewerPage.goto(`${INSIGHTS_PATH}/workbook`)
		await expect(viewerPage.getByText(workbook.title)).toBeVisible()
	})
})
