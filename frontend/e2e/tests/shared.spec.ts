import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'
import {
	buildChartDataQuery,
	publishChart,
	publishDashboard,
	unpublishDashboard,
} from '../helpers/insights'

test.describe('shared', () => {
	test('a logged-out visitor opens a shared dashboard link and sees charts', async ({
		guestPage,
		adminApi,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { chart, dashboard } = workbookWithDashboard
		await buildChartDataQuery(adminApi, chart)
		await publishDashboard(adminApi, dashboard.name)

		await guestPage.goto(`${INSIGHTS_PATH}/shared/dashboard/${dashboard.name}`)

		await expect(guestPage.getByText(chart.title)).toBeVisible()

		// locator: echarts writes `_echarts_instance_` on the element it renders
		// into, so this names the chart and nothing else on the page.
		const rendered = guestPage.locator('[_echarts_instance_]')
		// The Chart counts orders by status, so each status is a category label
		// and a real text node. The first execution runs a query, which takes
		// longer than the default assertion timeout allows.
		await expect(rendered.getByText('delivered')).toBeVisible({ timeout: 30_000 })
		await expect(rendered.getByText('shipped')).toBeVisible()
		await expect(rendered.getByText('canceled')).toBeVisible()
	})

	test('a logged-out visitor opens a shared chart link', async ({
		guestPage,
		adminApi,
		demoDataSource,
		workbookWithChart,
	}) => {
		const { chart } = workbookWithChart
		await buildChartDataQuery(adminApi, chart)
		await publishChart(adminApi, chart.name)

		await guestPage.goto(`${INSIGHTS_PATH}/shared/chart/${chart.name}`)

		// locator: echarts writes `_echarts_instance_` on the element it renders
		// into, so this names the chart and nothing else on the page.
		const rendered = guestPage.locator('[_echarts_instance_]')
		await expect(rendered.getByText('delivered')).toBeVisible({ timeout: 30_000 })
		await expect(rendered.getByText('shipped')).toBeVisible()
		await expect(rendered.getByText('canceled')).toBeVisible()
	})

	test('a revoked public link stops working', async ({
		guestPage,
		adminApi,
		demoDataSource,
		workbookWithDashboard,
	}) => {
		const { chart, dashboard } = workbookWithDashboard
		const link = `${INSIGHTS_PATH}/shared/dashboard/${dashboard.name}`

		await buildChartDataQuery(adminApi, chart)
		await publishDashboard(adminApi, dashboard.name)
		await guestPage.goto(link)
		await expect(guestPage.getByText(chart.title)).toBeVisible()

		await unpublishDashboard(adminApi, dashboard.name)
		await guestPage.goto(link)

		// The withdrawn dashboard answers a Guest with a 403, and the app sends
		// the visitor to the site login page. There is no 403 screen.
		await expect(guestPage).toHaveURL(/\/login/)
		// The login page draws its sign-in prompt twice, once per card, so this
		// asserts the prompt is present rather than that one node is visible.
		await expect(guestPage.getByText('Please sign in to continue')).not.toHaveCount(0)
		await expect(guestPage.getByText(chart.title)).toHaveCount(0)
	})
})
