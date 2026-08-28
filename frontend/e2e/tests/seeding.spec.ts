import { expect, test } from '../fixtures'
import { VIEWER_EMAIL } from '../helpers/auth'
import { DOCTYPE } from '../helpers/insights'

/**
 * The seeding layer checking itself. Every assertion here is over REST, so this
 * spec fails for a seeding reason and never for a rendering one.
 */
test.describe('seeding', () => {
	test('gives a test a Workbook with one Query over the demo Data Source', async ({
		adminApi,
		workbookWithQuery,
	}) => {
		const query = await adminApi.getDoc<{ workbook: string; title: string }>(
			DOCTYPE.QUERY,
			workbookWithQuery.query.name,
		)
		expect(query.workbook).toBe(workbookWithQuery.workbook.name)
		expect(query.title).toBe(workbookWithQuery.query.title)
	})

	test('gives a test a saved Chart over that Query', async ({ adminApi, workbookWithChart }) => {
		const chart = await adminApi.getDoc<{
			query: string
			chart_type: string
			workbook: string
		}>(DOCTYPE.CHART, workbookWithChart.chart.name)
		expect(chart.query).toBe(workbookWithChart.query.name)
		expect(chart.workbook).toBe(workbookWithChart.workbook.name)
		expect(chart.chart_type).toBe('Bar')
	})

	test('signs the viewer in as its own Insights user', async ({ viewerApi }) => {
		const own = await viewerApi.getDoc<{ name: string }>(DOCTYPE.USER, VIEWER_EMAIL)
		expect(own.name).toBe(VIEWER_EMAIL)
	})
})
