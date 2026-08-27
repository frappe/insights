import type { Locator, Page } from '@playwright/test'
import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'
import { createChart, createDashboard, uniqueTitle } from '../helpers/insights'

/**
 * A dashboard item is a grid cell from grid-layout-plus, which gives it no role
 * and no accessible name. Scoping to it also keeps the workbook sidebar, which
 * lists the same chart titles, out of every assertion.
 */
// locator: grid-layout-plus renders plain divs and names them only by class.
const items = (page: Page): Locator => page.locator('.vgl-item')

/**
 * The chart itself. echarts writes `_echarts_instance_` on the element it
 * renders into, so this names the charts and nothing else on the page.
 */
// locator: an echarts canvas host carries no role and no accessible name.
const charts = (page: Page): Locator => page.locator('[_echarts_instance_]')

/**
 * The panel a Popover opens. reka portals it to the body and marks only the
 * wrapper, so nothing inside it is reachable from the trigger.
 */
// locator: reka's popper wrapper has no role of its own.
const popover = (page: Page): Locator => page.locator('[data-reka-popper-content-wrapper]')

test.describe('dashboard', () => {
	test('a dashboard loads with all charts rendered', async ({
		page,
		demoDataSource,
		adminApi,
		workbookWithChart,
	}) => {
		const { workbook, query, chart } = workbookWithChart
		const second = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			title: uniqueTitle('Second Chart'),
		})
		const dashboard = await createDashboard(adminApi, {
			workbook: workbook.name,
			charts: [chart.name, second.name],
		})

		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)

		await expect(items(page).filter({ hasText: chart.title })).toHaveCount(1)
		await expect(items(page).filter({ hasText: second.title })).toHaveCount(1)

		await expect(charts(page)).toHaveCount(2)
		// Both charts count the 2,000 demo orders by status, and 1,778 of them are
		// delivered, so each value axis runs to a 1.8K tick. A category label is
		// not safe to assert on here, because echarts drops the ones that would
		// overlap at a dashboard item's width. The first execution runs a query,
		// so it takes longer than the default assertion timeout allows.
		await expect(charts(page).getByText('1.8K')).toHaveCount(2, { timeout: 30_000 })
	})

	test('a user creates a dashboard and adds a chart', async ({
		page,
		demoDataSource,
		workbookWithChart,
	}) => {
		const { workbook, chart } = workbookWithChart
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)
		await expect(page.getByRole('link', { name: chart.title })).toBeVisible()

		await page.getByRole('button', { name: 'Add Dashboards' }).click()

		// A new dashboard is named after its position in the workbook.
		await expect(page.getByRole('link', { name: 'Dashboard 1' })).toBeVisible()

		await page.getByRole('button', { name: 'Edit', exact: true }).click()
		await page.getByRole('button', { name: 'Chart', exact: true }).click()

		const selector = page.getByRole('dialog', { name: 'Select Charts' })
		await selector.getByText(chart.title).click()
		await selector.getByRole('button', { name: 'Add', exact: true }).click()

		await page.getByRole('button', { name: 'Done', exact: true }).click()

		await expect(items(page).filter({ hasText: chart.title })).toHaveCount(1)
		await expect(charts(page).getByText('1.8K')).toBeVisible({ timeout: 30_000 })
	})

	/**
	 * Building a filter and using one are two flows, not one. Building writes to
	 * the dashboard. Using a filter edits nothing at all, so it belongs on its
	 * own, over a filter the fixture seeded.
	 */
	test('a user adds a dashboard filter', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard, chart } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(charts(page).getByText('1.8K')).toBeVisible({ timeout: 30_000 })

		await page.getByRole('button', { name: 'Edit', exact: true }).click()
		await page.getByRole('button', { name: 'Filter', exact: true }).click()

		// Adding a filter opens its editor at once, because an unnamed filter
		// routes to nothing.
		const editor = page.getByRole('dialog', { name: 'Edit Filter' })

		// A linked chart row is keyed on the chart's name, which is empty
		// until the chart document loads. Waiting for the title keeps the
		// click off the row that the load replaces.
		await expect(editor.getByText(chart.title)).toBeVisible()

		await editor.getByLabel('Label').fill('Status')
		await editor.getByRole('switch').click()
		await editor.getByPlaceholder('Select a column').click()
		await page.getByRole('option', { name: 'order_status' }).click()
		await editor.getByRole('button', { name: 'Save', exact: true }).click()
		// Save writes the filter but leaves the editor open, so the flow
		// closes it.
		await editor.getByRole('button', { name: 'Close' }).click()

		// The control takes the label the moment the editor writes it back,
		// and keeps it once the dashboard leaves edit mode.
		await expect(page.getByRole('button', { name: 'Status', exact: true })).toBeVisible()
		await page.getByRole('button', { name: 'Done', exact: true }).click()
		await expect(page.getByRole('button', { name: 'Status', exact: true })).toBeVisible()
	})

	test('a linked chart refilters when a dashboard filter is applied', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithChart,
	}) => {
		const { workbook, query, chart } = workbookWithChart
		const dashboard = await createDashboard(adminApi, {
			workbook: workbook.name,
			charts: [chart.name],
			filters: [
				{ name: 'Status', chart: chart.name, query: query.name, column: 'order_status' },
			],
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)

		// Before the filter the chart counts every order by status, so its value
		// axis runs to the 1,778 delivered orders and tops out at a 1.8K tick.
		await expect(charts(page).getByText('1.8K')).toBeVisible({ timeout: 30_000 })

		await page.getByRole('button', { name: 'Status', exact: true }).click()
		await popover(page).getByText('canceled', { exact: true }).click()
		// locator: the apply button is icon-only and passes no label, so frappe-ui
		// renders it with no accessible name. Its lucide icon class is the name.
		await popover(page).locator('button:has(span.lucide-check)').click()

		// The chart now counts canceled orders alone, so `canceled` is the only
		// category left and the value axis no longer reaches the delivered scale.
		await expect(charts(page).getByText('canceled')).toBeVisible()
		await expect(charts(page).getByText('1.8K')).toHaveCount(0)
		// The filter states what it applied, on the control itself.
		await expect(page.getByRole('button', { name: 'Status in canceled' })).toBeVisible()
	})

	test('a user moves and resizes a dashboard item', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard, chart } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(charts(page).getByText('1.8K')).toBeVisible({ timeout: 30_000 })

		await page.getByRole('button', { name: 'Edit', exact: true }).click()

		const item = items(page).filter({ hasText: chart.title })
		const start = (await item.boundingBox())!

		// A grid item is its own drag handle. interact.js reads a pointer path, so
		// the move runs in steps and not as a single jump.
		await page.mouse.move(start.x + 40, start.y + 20)
		await page.mouse.down()
		await page.mouse.move(start.x + 240, start.y + 20, { steps: 20 })
		await page.mouse.up()

		await expect.poll(async () => (await item.boundingBox())!.x).toBeGreaterThan(start.x + 100)

		// locator: the resize grip is a bare div that grid-layout-plus names only
		// by class.
		const grip = item.locator('.vgl-item__resizer')
		const gripBox = (await grip.boundingBox())!
		await page.mouse.move(gripBox.x + 5, gripBox.y + 5)
		await page.mouse.down()
		await page.mouse.move(gripBox.x + 155, gripBox.y + 105, { steps: 20 })
		await page.mouse.up()

		await expect
			.poll(async () => (await item.boundingBox())!.height)
			.toBeGreaterThan(start.height + 50)

		const moved = (await item.boundingBox())!
		await page.getByRole('button', { name: 'Done', exact: true }).click()
		// Done saves and leaves edit mode, and the Edit button is what says so.
		await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible()
		await page.reload()

		// The layout survives the save, so the item comes back where it was left.
		await expect.poll(async () => (await item.boundingBox())!.x).toBeGreaterThan(start.x + 100)
		await expect.poll(async () => (await item.boundingBox())!.height).toBe(moved.height)
	})

	test('a user adds a text block', async ({ page, demoDataSource, workbookWithDashboard }) => {
		const { workbook, dashboard } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible()

		await page.getByRole('button', { name: 'Edit', exact: true }).click()
		await page.getByRole('button', { name: 'Text', exact: true }).click()

		// Adding a text block opens its editor at once, because an empty block
		// shows nothing to click.
		const editor = page.getByRole('dialog', { name: 'Edit Text' })
		await editor.getByRole('textbox').fill('Revenue holds through the quarter')
		await editor.getByRole('button', { name: 'Save', exact: true }).click()

		await page.getByRole('button', { name: 'Done', exact: true }).click()

		await expect(page.getByText('Revenue holds through the quarter')).toBeVisible()
	})

	test('a user removes a dashboard item', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard, chart } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(charts(page).getByText('1.8K')).toBeVisible({ timeout: 30_000 })

		await page.getByRole('button', { name: 'Edit', exact: true }).click()

		const item = items(page).filter({ hasText: chart.title })
		await item.hover()
		// locator: the item actions are bare divs holding a lucide icon, so they
		// carry no role, no text and no label. The icon class is what names them.
		await item.locator('div:has(> svg.lucide-trash-2)').click()

		await expect(items(page)).toHaveCount(0)
		await expect(charts(page)).toHaveCount(0)

		await page.getByRole('button', { name: 'Done', exact: true }).click()
		// Done saves and leaves edit mode, and the Edit button is what says so.
		await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible()
		await page.reload()

		await expect(charts(page)).toHaveCount(0)
	})

	test('a user shares a dashboard and opens the public link', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)

		// The workbook header carries its own Share button, and only the
		// dashboard's one names itself through a label.
		const shareButton = page.getByLabel('Share', { exact: true })
		await expect(shareButton).toBeVisible()
		await shareButton.click()

		const share = page.getByRole('dialog', { name: 'Share Dashboard' })
		await share.getByPlaceholder('Select an option').click()
		await page.getByRole('option', { name: 'Anyone with the link can view' }).click()

		// The toast fires before the write returns, and nothing else on the page
		// reports it, so the flow waits on the write itself. This is a wait, not
		// an assertion: every assertion below reads the interface.
		const written = page.waitForResponse((response) =>
			(response.request().postData() || '').includes('update_access'),
		)
		await share.getByRole('button', { name: 'Done', exact: true }).click()
		await expect(page.getByText('Dashboard Access Updated')).toBeVisible()
		await written

		// The dialog reads the access once, when it mounts, so a fresh page is
		// what proves the link is stored and not just held in the tab.
		await page.reload()
		await shareButton.click()
		await expect(share.getByPlaceholder('Select an option')).toHaveValue(
			'Anyone with the link can view',
		)
	})

	test('a dashboard filter with no linked chart changes nothing', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(charts(page).getByText('1.8K')).toBeVisible({ timeout: 30_000 })

		await page.getByRole('button', { name: 'Edit', exact: true }).click()
		await page.getByRole('button', { name: 'Filter', exact: true }).click()

		// The filter is saved with its Linked Charts switch left off.
		const editor = page.getByRole('dialog', { name: 'Edit Filter' })
		await editor.getByLabel('Label').fill('Status')
		await expect(editor.getByLabel('Label')).toHaveValue('Status')
		await editor.getByRole('button', { name: 'Save', exact: true }).click()
		// Save writes the filter but leaves the editor open, so the flow closes it.
		await editor.getByRole('button', { name: 'Close' }).click()

		// The control takes the label the moment the editor writes it back.
		await expect(page.getByRole('button', { name: 'Status', exact: true })).toBeVisible()
		await page.getByRole('button', { name: 'Done', exact: true }).click()

		await page.getByRole('button', { name: 'Status', exact: true }).click()

		// No linked chart names a column, so the filter can read no values from
		// the data and offers none of the order statuses to pick.
		await expect(popover(page).getByPlaceholder('Search')).toBeVisible()
		await expect(popover(page).getByText('delivered')).toHaveCount(0)
		await expect(popover(page).getByText('canceled')).toHaveCount(0)

		// A typed value applies all the same, and nothing tells the user that the
		// filter reaches no chart.
		await popover(page).getByRole('combobox').click()
		await page.getByRole('option', { name: 'equals', exact: true }).click()
		await popover(page).getByPlaceholder('Value').fill('canceled')
		// locator: the apply button is icon-only and passes no label, so frappe-ui
		// renders it with no accessible name. Its lucide icon class is the name.
		await popover(page).locator('button:has(span.lucide-check)').click()

		await expect(page.getByRole('button', { name: 'Status = canceled' })).toBeVisible()
		// The chart still counts every order, so its value axis keeps the 1.8K
		// tick that the 1,778 delivered orders set.
		await expect(charts(page).getByText('1.8K')).toBeVisible()
	})
})
