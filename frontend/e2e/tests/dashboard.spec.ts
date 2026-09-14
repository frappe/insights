import type { Locator, Page } from '@playwright/test'
import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'
import { createChart, createDashboard, uniqueTitle } from '../helpers/insights'

/**
 * A dashboard item is a grid cell `StaticGridLayout` places, which gives it no
 * role and no accessible name. Scoping to it also keeps the workbook sidebar,
 * which lists the same chart titles, out of every assertion.
 */
const items = (page: Page): Locator => page.getByTestId('dashboard-cell')

/**
 * The chart itself. echarts writes `_echarts_instance_` on the element it
 * renders into, so this names the charts and nothing else on the page.
 */
// locator: an echarts host carries no role and no accessible name.
const charts = (page: Page): Locator => page.locator('[_echarts_instance_]')

/**
 * The panel a Popover opens. reka portals it to the body and marks only the
 * wrapper, so nothing inside it is reachable from the trigger.
 */
// locator: reka's popper wrapper has no role of its own.
const popover = (page: Page): Locator => page.locator('[data-reka-popper-content-wrapper]')

test.describe('dashboard', () => {
	// @feature dashboard.loads
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
		// delivered, so each value axis runs to a 1,800 tick. A category label is
		// not safe to assert on here, because echarts drops the ones that would
		// overlap at a dashboard item's width. The first execution runs a query,
		// so it takes longer than the default assertion timeout allows.
		await expect(charts(page).getByText('1,800')).toHaveCount(2, { timeout: 30_000 })
	})

	// @feature dashboard.create-add-chart dashboard.chart-selector
	test('a user creates a dashboard and adds a chart', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithChart,
	}) => {
		const { workbook, query, chart } = workbookWithChart
		const second = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			title: uniqueTitle('Second Chart'),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)
		await expect(page.getByRole('link', { name: chart.title })).toBeVisible()

		await page.getByRole('button', { name: 'Add Dashboards' }).click()

		// A new dashboard is named after its position in the workbook.
		await expect(page.getByRole('link', { name: 'Dashboard 1' })).toBeVisible()

		await page.getByRole('button', { name: 'Edit', exact: true }).click()
		await page.getByRole('button', { name: 'Chart', exact: true }).click()

		// The selector searches the workbook's charts by title, and keeps only the
		// ones that match.
		const selector = page.getByRole('dialog', { name: 'Select Charts' })
		await selector.getByPlaceholder('Search by name').fill(second.title)
		await expect(selector.getByText(second.title)).toBeVisible()
		await expect(selector.getByText(chart.title)).toHaveCount(0)

		// Select All reads the whole list, not the search, so the cleared search
		// is what makes the two counts agree.
		await selector.getByPlaceholder('Search by name').fill('')
		await selector.getByRole('button', { name: /Select All/ }).click()
		await selector.getByRole('button', { name: 'Add', exact: true }).click()

		await page.getByRole('button', { name: 'Done', exact: true }).click()

		await expect(items(page).filter({ hasText: chart.title })).toHaveCount(1)
		await expect(items(page).filter({ hasText: second.title })).toHaveCount(1)
		// Both charts count the 2,000 demo orders by status, and 1,778 of them are
		// delivered, so each value axis runs to a 1,800 tick.
		await expect(charts(page).getByText('1,800')).toHaveCount(2, { timeout: 30_000 })
	})

	/**
	 * Building a filter and using one are two flows, not one. Building writes to
	 * the dashboard. Using a filter edits nothing at all, so it belongs on its
	 * own, over a filter the fixture seeded.
	 */
	// @feature dashboard.filter-add
	test('a user adds a dashboard filter', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard, chart } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(charts(page).getByText('1,800')).toBeVisible({ timeout: 30_000 })

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
		// Save writes the filter back and closes the editor with it.
		await editor.getByRole('button', { name: 'Save', exact: true }).click()
		await expect(editor).toBeHidden()

		// The control takes the label the moment the editor writes it back,
		// and keeps it once the dashboard leaves edit mode.
		await expect(page.getByRole('button', { name: 'Status', exact: true })).toBeVisible()
		await page.getByRole('button', { name: 'Done', exact: true }).click()
		await expect(page.getByRole('button', { name: 'Status', exact: true })).toBeVisible()
	})

	// @feature dashboard.filter-links dashboard.filter-clear
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
		// axis runs to the 1,778 delivered orders and tops out at a 1,800 tick.
		await expect(charts(page).getByText('1,800')).toBeVisible({ timeout: 30_000 })

		// A filter that names its column opens on the operator, then on the values
		// that column holds. A value list commits when the panel closes, and the
		// trigger is what closes it.
		const trigger = page.getByRole('button', { name: 'Status', exact: true })
		await trigger.click()
		await page.getByRole('option', { name: 'is', exact: true }).click()
		await page.getByRole('option', { name: 'canceled' }).click()
		await trigger.click()

		// The chart now counts canceled orders alone, so `canceled` is the only
		// category left and the value axis no longer reaches the delivered scale.
		await expect(charts(page).getByText('canceled')).toBeVisible()
		await expect(charts(page).getByText('1,800')).toHaveCount(0)
		// The filter states what it applied, on the control itself.
		await expect(page.getByRole('button', { name: 'Status is canceled' })).toBeVisible()

		// Clear sits beside the trigger, so it takes the value off without
		// opening the picker. The chart widens back to every order.
		await page.getByRole('button', { name: 'Clear' }).click()

		await expect(trigger).toBeVisible()
		await expect(page.getByRole('button', { name: 'Status is canceled' })).toHaveCount(0)
		await expect(charts(page).getByText('1,800')).toBeVisible({ timeout: 30_000 })
	})

	// @feature dashboard.move-resize dashboard.reset-layout
	test('a user moves and resizes a dashboard item', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard, chart } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(charts(page).getByText('1,800')).toBeVisible({ timeout: 30_000 })

		await page.getByRole('button', { name: 'Edit', exact: true }).click()

		const item = items(page).filter({ hasText: chart.title })
		const start = (await item.boundingBox())!

		// A grid item is its own drag handle. The grid follows the pointer, so the
		// move runs in steps and not as a single jump.
		await page.mouse.move(start.x + 40, start.y + 20)
		await page.mouse.down()
		await page.mouse.move(start.x + 240, start.y + 20, { steps: 20 })
		await page.mouse.up()

		await expect.poll(async () => (await item.boundingBox())!.x).toBeGreaterThan(start.x + 100)

		const grip = item.getByTestId('dashboard-cell-resize')
		const gripBox = (await grip.boundingBox())!
		await page.mouse.move(gripBox.x + 5, gripBox.y + 5)
		await page.mouse.down()
		await page.mouse.move(gripBox.x + 155, gripBox.y + 105, { steps: 20 })
		await page.mouse.up()

		await expect
			.poll(async () => (await item.boundingBox())!.height)
			.toBeGreaterThan(start.height + 50)

		const moved = (await item.boundingBox())!

		// Done leaves edit mode before the write it starts has answered, and the
		// reload below would cut a write still in flight. The Dashboard's own
		// `set_value` is the only signal it landed — nothing on screen says so.
		const written = page.waitForResponse(
			(response) =>
				response.url().includes('/api/method/frappe.client.set_value') &&
				response.request().postDataJSON()?.doctype === 'Insights Dashboard v3',
		)
		await page.getByRole('button', { name: 'Done', exact: true }).click()
		// Done saves and leaves edit mode, and the Edit button is what says so.
		await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible()
		await written
		await page.reload()

		// The layout survives the save, so the item comes back where it was left.
		await expect.poll(async () => (await item.boundingBox())!.x).toBeGreaterThan(start.x + 100)
		await expect.poll(async () => (await item.boundingBox())!.height).toBe(moved.height)

		// The box the save wrote, read outside edit mode: entering edit mode
		// insets the grid, so a box measured there is a different number for the
		// same layout.
		const saved = (await item.boundingBox())!

		// Reset Layout throws the unsaved move away and leaves edit mode, so the
		// item goes back to the box the last save wrote.
		await page.getByRole('button', { name: 'Edit', exact: true }).click()
		const again = (await item.boundingBox())!
		await page.mouse.move(again.x + 40, again.y + 20)
		await page.mouse.down()
		await page.mouse.move(again.x - 160, again.y + 20, { steps: 20 })
		await page.mouse.up()
		await expect.poll(async () => (await item.boundingBox())!.x).toBeLessThan(again.x - 50)

		// locator: the dashboard's overflow menu is an icon-only Button with no
		// accessible name, and the workbook navbar above it holds a second menu
		// trigger. The dashboard's own title row is what tells them apart.
		await page.locator('div.h-7.mx-4 button[aria-haspopup="menu"]').click()
		await page.getByRole('menuitem', { name: 'Reset Layout' }).click()

		// Throwing the arrangement away is a confirm, because there is no undo
		// once the edit session ends.
		const discard = page.getByRole('dialog', { name: 'Discard Changes' })
		await expect(discard.getByText('Are you sure you want to discard changes?')).toBeVisible()
		await discard.getByRole('button', { name: 'Confirm' }).click()

		await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible()
		await expect.poll(async () => (await item.boundingBox())!.x).toBe(saved.x)
		await expect.poll(async () => (await item.boundingBox())!.height).toBe(saved.height)
	})

	// @feature dashboard.text-block
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

	// @feature dashboard.remove-item
	test('a user removes a dashboard item', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard, chart } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(charts(page).getByText('1,800')).toBeVisible({ timeout: 30_000 })

		await page.getByRole('button', { name: 'Edit', exact: true }).click()

		const item = items(page).filter({ hasText: chart.title })
		await item.hover()
		// The item's action bar draws real buttons, and each one carries the
		// label of the act it performs.
		await item.getByRole('button', { name: 'Delete' }).click()

		await expect(items(page)).toHaveCount(0)
		await expect(charts(page)).toHaveCount(0)

		await page.getByRole('button', { name: 'Done', exact: true }).click()
		// Done saves and leaves edit mode, and the Edit button is what says so.
		await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible()
		await page.reload()

		await expect(charts(page)).toHaveCount(0)
	})

	// @feature shared.dashboard-link
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

	// @feature dashboard.filter-links
	test('a dashboard filter with no linked chart changes nothing', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(charts(page).getByText('1,800')).toBeVisible({ timeout: 30_000 })

		await page.getByRole('button', { name: 'Edit', exact: true }).click()
		await page.getByRole('button', { name: 'Filter', exact: true }).click()

		// The filter is saved with its Linked Charts switch left off.
		const editor = page.getByRole('dialog', { name: 'Edit Filter' })
		await editor.getByLabel('Label').fill('Status')
		await expect(editor.getByLabel('Label')).toHaveValue('Status')
		// Save writes the filter back and closes the editor with it.
		await editor.getByRole('button', { name: 'Save', exact: true }).click()
		await expect(editor).toBeHidden()

		// The control takes the label the moment the editor writes it back.
		await expect(page.getByRole('button', { name: 'Status', exact: true })).toBeVisible()
		await page.getByRole('button', { name: 'Done', exact: true }).click()

		// The filter names its own column, so the picker opens on the operator.
		const trigger = page.getByRole('button', { name: 'Status', exact: true })
		await trigger.click()
		await page.getByRole('option', { name: 'is', exact: true }).click()

		// No linked chart names a column, so the filter can read no values from
		// the data and offers none of the order statuses to pick.
		await expect(popover(page).getByText('No values found')).toBeVisible()
		await expect(popover(page).getByText('delivered')).toHaveCount(0)
		await expect(popover(page).getByText('canceled')).toHaveCount(0)

		// A typed value applies all the same, and nothing tells the user that the
		// filter reaches no chart. The trigger closes the picker, which reopens
		// on the operator, and `equals` is the one that takes a typed value.
		await trigger.click()
		await trigger.click()
		// An operator row reads as its word, with its sign beside it.
		await page.getByRole('option', { name: 'equals =', exact: true }).click()
		await popover(page).getByRole('combobox').fill('canceled')
		// The typed rule is a row of its own, and picking it applies the filter.
		await page.getByRole('option', { name: /canceled/ }).click()

		await expect(page.getByRole('button', { name: 'Status equals canceled' })).toBeVisible()
		// The chart still counts every order, so its value axis keeps the 1,800
		// tick that the 1,778 delivered orders set.
		await expect(charts(page).getByText('1,800')).toBeVisible()
	})

	// @feature dashboard.drag-chart-from-sidebar
	test('a user drags a chart from the sidebar onto the grid', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithChart,
	}) => {
		const { workbook, chart } = workbookWithChart
		const dashboard = await createDashboard(adminApi, {
			workbook: workbook.name,
			charts: [],
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/dashboard/${dashboard.name}`)
		await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible()

		await page.getByRole('button', { name: 'Edit', exact: true }).click()
		await expect(items(page)).toHaveCount(0)

		// locator: the grid's host is the only scrolling box on the dashboard and
		// carries no role. It is the drop target, and an empty dashboard draws no
		// grid inside it, so there is nothing else to aim at.
		const grid = page.locator('div.overflow-y-auto.p-2.pt-0')
		await page.getByRole('link', { name: chart.title }).dragTo(grid)

		await expect(items(page).filter({ hasText: chart.title })).toHaveCount(1)

		// Done leaves edit mode as soon as it is clicked, so the Edit button is
		// back before the write it started returns. This is a wait, not an
		// assertion: reloading ahead of the write reads a dashboard that never
		// got the card.
		const written = page.waitForResponse((response) =>
			response.url().includes('frappe.client.set_value'),
		)
		await page.getByRole('button', { name: 'Done', exact: true }).click()
		await expect(page.getByRole('button', { name: 'Edit', exact: true })).toBeVisible()
		await written
		await page.reload()

		await expect(items(page).filter({ hasText: chart.title })).toHaveCount(1)
		await expect(charts(page).getByText('1,800')).toBeVisible({ timeout: 30_000 })
	})

	// @feature dashboard.edit-chart dashboard.open-workbook
	test('a reader with access opens the chart and the workbook behind a dashboard card', async ({
		page,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { workbook, dashboard, chart } = workbookWithDashboard
		await page.goto(`${INSIGHTS_PATH}/dashboards/${dashboard.name}`)

		const card = items(page).filter({ hasText: chart.title })
		await expect(card).toHaveCount(1)
		await card.hover()
		// locator: the pencil that opens the chart is an icon-only Button inside a
		// Tooltip, so it carries no accessible name. Its lucide icon class names
		// it inside the card it belongs to.
		await card.locator('button:has(svg.lucide-pencil)').click()

		await expect(page).toHaveURL(new RegExp(`/workbook/${workbook.name}/chart/${chart.name}$`))

		await page.goBack()
		await expect(items(page).filter({ hasText: chart.title })).toHaveCount(1)

		// locator: the dashboard header's overflow menu is an icon-only Button
		// with no accessible name. `aria-haspopup` marks it as the header's only
		// menu trigger.
		await page.getByRole('banner').locator('button[aria-haspopup="menu"]').click()
		await page.getByRole('menuitem', { name: 'Open Workbook' }).click()

		await expect(page).toHaveURL(new RegExp(`/workbook/${workbook.name}`))
	})
})
