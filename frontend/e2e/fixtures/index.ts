import { test as base, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { readCsrfToken, storageStatePath } from '../helpers/auth'
import { createFrappeApi, type FrappeApi } from '../helpers/frappe'
import {
	DEMO_DATA_SOURCE,
	assertDemoData,
	createChart,
	createDashboard,
	createQuery,
	createWorkbook,
	deleteWorkbook,
	type SeededChart,
	type SeededDashboard,
	type SeededQuery,
	type SeededWorkbook,
} from '../helpers/insights'

export type WorkbookWithQuery = { workbook: SeededWorkbook; query: SeededQuery }
export type WorkbookWithChart = WorkbookWithQuery & { chart: SeededChart }
export type WorkbookWithDashboard = WorkbookWithChart & { dashboard: SeededDashboard }

export type InsightsFixtures = {
	/** REST as the admin. Seeding runs here, never through the browser. */
	adminApi: FrappeApi
	/** REST as an Insights User with no admin rights. */
	viewerApi: FrappeApi
	/** A browser page signed in as the viewer. */
	viewerPage: Page
	/** A browser page with no session at all. What a link recipient sees. */
	guestPage: Page
	/** The demo Data Source, checked to exist and to have its tables synced. */
	demoDataSource: string
	/** An empty Workbook. Deleted after the test, with everything inside it. */
	workbook: SeededWorkbook
	/** A Workbook holding one Query over the demo Data Source. */
	workbookWithQuery: WorkbookWithQuery
	/** A Workbook holding one Query and one saved Chart over it. */
	workbookWithChart: WorkbookWithChart
	/** A Workbook holding one Query, one Chart, and a Dashboard showing it. */
	workbookWithDashboard: WorkbookWithDashboard
}

/**
 * Fixtures scoped to business actions.
 *
 * Each rung of the Workbook ladder builds on the one below it, so a test that
 * asks for a Chart gets exactly one Workbook and one teardown. A test states
 * what it depends on by naming the fixture, and nothing is seeded that a test
 * did not ask for.
 */
export const test = base.extend<InsightsFixtures>({
	adminApi: async ({ playwright, baseURL }, use) => {
		const context = await playwright.request.newContext({
			baseURL,
			storageState: storageStatePath('admin'),
		})
		await use(createFrappeApi(context, readCsrfToken('admin')))
		await context.dispose()
	},

	viewerApi: async ({ playwright, baseURL }, use) => {
		const context = await playwright.request.newContext({
			baseURL,
			storageState: storageStatePath('viewer'),
		})
		await use(createFrappeApi(context, readCsrfToken('viewer')))
		await context.dispose()
	},

	viewerPage: async ({ browser }, use) => {
		const context = await browser.newContext({ storageState: storageStatePath('viewer') })
		const page = await context.newPage()
		await use(page)
		await context.close()
	},

	guestPage: async ({ browser, baseURL }, use) => {
		// An empty storage state, not the project default. The `page` fixture
		// carries the admin session, so a guest flow that reused it would prove
		// nothing. `browser.newContext` takes no options from the config, so
		// `baseURL` is passed on.
		const context = await browser.newContext({
			baseURL,
			storageState: { cookies: [], origins: [] },
		})
		const page = await context.newPage()
		await use(page)
		await context.close()
	},

	demoDataSource: async ({ adminApi }, use) => {
		await assertDemoData(adminApi)
		await use(DEMO_DATA_SOURCE)
	},

	workbook: async ({ adminApi }, use) => {
		const workbook = await createWorkbook(adminApi)
		await use(workbook)
		await deleteWorkbook(adminApi, workbook.name)
	},

	workbookWithQuery: async ({ adminApi, demoDataSource, workbook }, use) => {
		const query = await createQuery(adminApi, {
			workbook: workbook.name,
			dataSource: demoDataSource,
		})
		await use({ workbook, query })
	},

	workbookWithChart: async ({ adminApi, workbookWithQuery }, use) => {
		const chart = await createChart(adminApi, {
			workbook: workbookWithQuery.workbook.name,
			query: workbookWithQuery.query.name,
		})
		await use({ ...workbookWithQuery, chart })
	},

	workbookWithDashboard: async ({ adminApi, workbookWithChart }, use) => {
		const dashboard = await createDashboard(adminApi, {
			workbook: workbookWithChart.workbook.name,
			charts: [workbookWithChart.chart.name],
		})
		await use({ ...workbookWithChart, dashboard })
	},
})

export { expect }
