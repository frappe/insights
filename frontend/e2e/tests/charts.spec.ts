import type { Locator, Page } from '@playwright/test'
import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'
import { createChart, type ChartConfig, type Dimension, type Measure } from '../helpers/insights'

/**
 * A section of the chart config sidebar.
 *
 * locator: every section holds controls that read "Select a column", so a name
 * alone reaches several of them. A section's own heading is the only thing that
 * tells its controls apart, and the heading is a plain button holding a `<p>`.
 */
function section(page: Page, title: string): Locator {
	return page.locator(`div.flex.flex-col:has(> button > div > p:text-is("${title}"))`)
}

/**
 * The chart itself, and nothing else on the page.
 *
 * locator: echarts writes `_echarts_instance_` on the element it renders into.
 * The result preview under the chart builder repeats every category label, so
 * an unscoped getByText would reach both.
 */
function chartOf(page: Page): Locator {
	return page.locator('[_echarts_instance_]')
}

/**
 * The rows of the result preview under the chart.
 *
 * locator: `<thead>` uses `<td>`, and `<tbody>` ends with a cell-less spacer
 * row, so role=row over-counts. `:has(td)` keeps only real data rows.
 */
function previewRows(page: Page): Locator {
	return page.locator('tbody tr:has(td)')
}

/**
 * Hold the first `set_value` for `doctype` open until `release` is called, and
 * record the title every such write carried. An edit made between `started`
 * and `release` lands while that write is in flight.
 *
 * A chart title also rewrites its Workbook, so the doctype filter is what keeps
 * the record to the Chart's own writes.
 */
function holdFirstWrite(page: Page, doctype: string) {
	let release = () => {}
	let markStarted = () => {}
	const held = new Promise<void>((resolve) => (release = resolve))
	const started = new Promise<void>((resolve) => (markStarted = resolve))
	const titles: string[] = []

	const routed = page.route('**/api/method/frappe.client.set_value', async (route) => {
		const body = route.request().postDataJSON()
		if (body?.doctype !== doctype) {
			return route.continue()
		}
		titles.push(String(body.fieldname?.title))
		if (titles.length === 1) {
			markStarted()
			await held
		}
		await route.continue()
	})

	return { routed, started, release, titles }
}

const COUNT_OF_ROWS: Measure = {
	measure_name: 'count_of_rows',
	column_name: 'count',
	data_type: 'Integer',
	aggregation: 'count',
}

const ORDER_STATUS: Dimension = {
	dimension_name: 'order_status',
	column_name: 'order_status',
	data_type: 'String',
}

function purchaseDate(granularity: string): Dimension {
	return {
		dimension_name: 'order_purchase_timestamp',
		column_name: 'order_purchase_timestamp',
		data_type: 'Datetime',
		granularity,
	}
}

/** The smallest Bar chart configuration: a row count split by one dimension. */
function barConfig(dimension: Dimension, extra: ChartConfig = {}): ChartConfig {
	return {
		x_axis: { dimension },
		y_axis: { series: [{ measure: COUNT_OF_ROWS }] },
		...extra,
	}
}

test.describe('charts', () => {
	test('a user creates a Bar chart with one dimension and one measure', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		await page.getByRole('button', { name: 'Add Charts' }).click()

		await page.getByRole('button', { name: 'Bar', exact: true }).click()

		const xAxis = section(page, 'X Axis')
		await xAxis.getByRole('button', { name: 'Select a column' }).click()
		await page.getByRole('option', { name: 'order_status' }).click()

		const yAxis = section(page, 'Y Axis')
		await yAxis.getByRole('button', { name: 'Select a column' }).click()
		// "Unique Count of..." holds the same words, so match the whole string.
		await page.getByText('Count of...', { exact: true }).click()
		const measureDialog = page.getByRole('dialog', { name: 'Select a column' })
		await measureDialog.getByText('order_id', { exact: true }).click()

		const chart = chartOf(page)

		// The chart renders as SVG, so a category label is a real <text> node.
		// Category order changes between runs, so nothing here depends on it.
		await expect(chart.getByText('delivered')).toBeVisible()
		await expect(chart.getByText('canceled')).toBeVisible()
		// The measure is the count of orders, and 1,778 of the 2,000 are
		// delivered, so the value axis runs to a 1.8K tick.
		await expect(chart.getByText('1.8K')).toBeVisible()
	})

	test('a user creates a Number chart and sees the value', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		await page.getByRole('button', { name: 'Add Charts' }).click()
		await page.getByRole('button', { name: 'Number', exact: true }).click()

		// locator: the Options section holds a measure picker under "Columns" and
		// a date picker under "Date". Both read "Select a column", and the
		// heading above each one is the only thing that tells them apart.
		const numberColumns = page.locator('div:has(> p:text-is("Columns"))')
		await numberColumns.getByRole('button', { name: 'Select a column' }).click()
		await page.getByText('Count of...', { exact: true }).click()
		const measureDialog = page.getByRole('dialog', { name: 'Select a column' })
		await measureDialog.getByText('order_id', { exact: true }).click()

		// locator: a Number chart draws plain HTML, not echarts, so there is no
		// `_echarts_instance_` to scope to. Its root is the page's only
		// `@container`, and `@` needs an attribute match because it is not a
		// valid class token in a CSS selector.
		const numberChart = page.locator('[class*="@container"]')
		await expect(numberChart.getByText('count_of_order_id')).toBeVisible()
		// All 2,000 demo orders carry an order_id, and a card spells its value
		// out in full unless the flow turns short numbers on.
		await expect(numberChart.getByText('2,000')).toBeVisible()
	})

	test('a user creates a Table chart with rows, columns and values', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		await page.getByRole('button', { name: 'Add Charts' }).click()
		await page.getByRole('button', { name: 'Table', exact: true }).click()

		await section(page, 'Rows').getByRole('button', { name: 'Select a column' }).click()
		await page.getByRole('option', { name: 'order_purchase_timestamp' }).click()

		await section(page, 'Values').getByRole('button', { name: 'Select a column' }).click()
		await page.getByText('Count of...', { exact: true }).click()
		const measureDialog = page.getByRole('dialog', { name: 'Select a column' })
		await measureDialog.getByText('order_id', { exact: true }).click()

		await section(page, 'Columns').getByRole('button', { name: 'Select a column' }).click()
		await page.getByRole('option', { name: 'order_status' }).click()

		// A Table chart draws the only table on the page, because the builder
		// drops its result preview for this type. The column dimension pivots the
		// measure into one column per order status, and the row dimension reads
		// at its month grain, which is the default for a date.
		await expect(page.getByRole('cell', { name: 'September, 2016' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'delivered' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'canceled' })).toBeVisible()
	})

	test('a user creates a Donut chart', async ({ page, demoDataSource, workbookWithQuery }) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		await page.getByRole('button', { name: 'Add Charts' }).click()
		await page.getByRole('button', { name: 'Donut', exact: true }).click()

		// locator: the Label and Value controls both read "Select a column". The
		// text above each one names it, and neither is a `<label for>`, so
		// getByLabel cannot reach the button.
		const labelPicker = page.locator('div:has(> label:text-is("Label"))')
		await labelPicker.getByRole('button', { name: 'Select a column' }).click()
		await page.getByRole('option', { name: 'order_status' }).click()

		const valuePicker = page.locator('div:has(> div:text-is("Value"))')
		await valuePicker.getByRole('button', { name: 'Select a column' }).click()
		await page.getByText('Count of...', { exact: true }).click()
		const measureDialog = page.getByRole('dialog', { name: 'Select a column' })
		await measureDialog.getByText('order_id', { exact: true }).click()

		// A Donut legend spells the share out beside the slice name. 1,778 of the
		// 2,000 orders are delivered, which rounds to 89%.
		const chart = chartOf(page)
		await expect(chart.getByText('delivered (89%)')).toBeVisible()
		await expect(chart.getByText('canceled (3%)')).toBeVisible()
	})

	test('a user changes chart type and config survives where it can', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Bar',
			config: barConfig(ORDER_STATUS, {
				filters: {
					logical_operator: 'And',
					filters: [
						{
							column: { type: 'column', column_name: 'order_status' },
							operator: '!=',
							value: 'unavailable',
						},
					],
				},
				limit: 42,
			}),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)

		const rendered = chartOf(page)
		await expect(rendered.getByText('delivered')).toBeVisible()
		await expect(rendered.getByText('1.8K')).toBeVisible()

		// Bar and Line are both axis charts, so the axis config carries over whole
		// and the new chart draws the same categories and the same value scale.
		await page.getByRole('button', { name: 'Line', exact: true }).click()
		await expect(rendered.getByText('delivered')).toBeVisible()
		await expect(rendered.getByText('1.8K')).toBeVisible()

		// Donut is not an axis chart, so crossing that boundary drops the axis
		// config and leaves the chart with nothing to draw.
		await page.getByRole('button', { name: 'Donut', exact: true }).click()
		await expect(
			page.getByText('Pick a chart type and configure options to see the chart here'),
		).toBeVisible()

		// The filter and the limit sit outside the type-specific config, so they
		// survive every switch. The count beside the heading is part of its name.
		await page.getByRole('button', { name: 'Filters 1' }).click()
		await expect(
			page.getByRole('button', { name: 'order_status != unavailable' }),
		).toBeVisible()

		await page.getByRole('button', { name: 'Limit', exact: true }).click()
		await expect(section(page, 'Limit').getByRole('spinbutton')).toHaveValue('42')
	})

	test('a user sets a date dimension granularity to month', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Bar',
			config: barConfig(purchaseDate('year')),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)

		// The demo orders run from 2016 to 2018, so a yearly grain gives three
		// rows and a value axis that reaches 1K.
		await expect(page.getByRole('cell', { name: '2016', exact: true })).toBeVisible()
		await expect(chartOf(page).getByText('1K')).toBeVisible()

		const xAxis = section(page, 'X Axis')
		// locator: the settings button beside the column picker is icon-only and
		// carries no accessible name. It is the only direct button child of the
		// picker's row, which is what names it here.
		await xAxis.locator('div.flex.items-end > button').click()
		// locator: the popover pairs a plain `<span>` with each control, so
		// nothing carries an accessible name. The row holding the "Granularity"
		// text is what names its select.
		await page
			.locator('div.flex:has(> span:text-is("Granularity"))')
			.getByRole('combobox')
			.click()
		await page.getByRole('option', { name: 'Month', exact: true }).click()

		// A month grain reads as "September, 2016", and the largest month holds
		// fewer than 100 orders, so the 1K tick is gone.
		await expect(page.getByRole('cell', { name: 'September, 2016' })).toBeVisible()
		await expect(page.getByRole('cell', { name: '2016', exact: true })).toHaveCount(0)
		await expect(chartOf(page).getByText('1K')).toHaveCount(0)
	})

	test('a user adds a split-by and sees series', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Bar',
			config: barConfig(purchaseDate('year')),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)

		const rendered = chartOf(page)
		await expect(rendered.getByText('2017')).toBeVisible()
		await expect(rendered.getByText('delivered')).toHaveCount(0)

		await section(page, 'Split Series').getByRole('button', { name: 'Select a column' }).click()
		await page.getByRole('option', { name: 'order_status' }).click()

		// The split turns one count into one series per order status, and each
		// series name reaches the legend as a real text node.
		await expect(rendered.getByText('delivered')).toBeVisible()
		await expect(rendered.getByText('canceled')).toBeVisible()
		await expect(rendered.getByText('unavailable')).toBeVisible()
	})

	test('a user adds a second measure', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Bar',
			config: barConfig(ORDER_STATUS),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)

		const rendered = chartOf(page)
		await expect(rendered.getByText('delivered')).toBeVisible()
		// One series draws no legend, so neither measure name is on the chart yet.
		await expect(rendered.getByText('count_of_rows')).toHaveCount(0)

		const yAxis = section(page, 'Y Axis')
		await yAxis.getByRole('button', { name: '+ Add series' }).click()
		await yAxis.getByRole('button', { name: 'Select a column' }).click()
		await page.getByText('Unique Count of...', { exact: true }).click()
		const measureDialog = page.getByRole('dialog', { name: 'Select a column' })
		await measureDialog.getByText('customer_id', { exact: true }).click()

		// Two series draw a legend, one entry per measure.
		await expect(rendered.getByText('count_of_rows')).toBeVisible()
		await expect(rendered.getByText('count_distinct_of_customer_id')).toBeVisible()
	})

	test('a user sorts a chart and flips it to descending', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Bar',
			config: barConfig(ORDER_STATUS),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)
		await expect(previewRows(page)).toHaveCount(6)

		// A chart sorts by the measure's name, not by the column it counts.
		await page.getByRole('button', { name: 'Sort', exact: true }).click()
		await page.getByRole('button', { name: 'Add Sort' }).click()
		await page.getByRole('option', { name: 'count_of_rows' }).click()

		// A new sort starts ascending, so the rarest status leads. 16 of the
		// 2,000 demo orders are unavailable.
		await expect(previewRows(page).first()).toContainText('unavailable')

		// locator: the direction toggle is icon-only and carries no accessible
		// name. It is the first button of the sort row, ahead of the column
		// picker and the remove button.
		await section(page, 'Sort').locator('div.flex.rounded > button:first-child').click()

		// Descending puts the most common status first. 1,778 orders are
		// delivered. The flip lands inside the save the sort above started, so
		// this asserts that the save answer keeps it.
		await expect(previewRows(page).first()).toContainText('delivered')
	})

	test('a user filters a chart independent of its query', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Bar',
			config: barConfig(ORDER_STATUS),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)

		const rendered = chartOf(page)
		await expect(rendered.getByText('delivered')).toBeVisible()

		await page.getByRole('button', { name: 'Filters', exact: true }).click()
		await page.getByRole('button', { name: 'Add Filter' }).click()
		const filterDialog = page.getByRole('dialog', { name: 'Filter' })
		await filterDialog.getByRole('button', { name: 'Add Filter' }).click()
		await filterDialog.getByRole('combobox', { name: 'Column' }).fill('order_status')
		await page.getByRole('option', { name: 'order_status' }).click()
		// The default operator for a text column is "is", which offers the
		// distinct values of the column.
		await filterDialog.getByRole('button', { name: 'Value' }).click()
		await page.getByRole('option', { name: 'canceled' }).click()
		await page.keyboard.press('Escape')
		await filterDialog.getByRole('button', { name: 'Apply Filters' }).click()

		// `canceled` is a category of the unfiltered chart too, so it says nothing
		// about the filter. Only `delivered` leaving proves it applied, and the
		// chart keeps drawing the old categories until the new result arrives.
		// That is a second query execution, which outlasts the default timeout
		// when five workers share the site.
		await expect(rendered.getByText('delivered')).toHaveCount(0, { timeout: 30_000 })
		await expect(rendered.getByText('canceled')).toBeVisible()

		// The filter belongs to the Chart, so the Query it reads keeps every row.
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)
		await expect(page.getByRole('cell', { name: 'delivered' })).not.toHaveCount(0)
	})

	test('a user creates a Line chart', async ({ page, demoDataSource, workbookWithQuery }) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		await page.getByRole('button', { name: 'Add Charts' }).click()
		await page.getByRole('button', { name: 'Line', exact: true }).click()

		await section(page, 'X Axis').getByRole('button', { name: 'Select a column' }).click()
		await page.getByRole('option', { name: 'order_purchase_timestamp' }).click()

		await section(page, 'Y Axis').getByRole('button', { name: 'Select a column' }).click()
		await page.getByText('Count of...', { exact: true }).click()
		const measureDialog = page.getByRole('dialog', { name: 'Select a column' })
		await measureDialog.getByText('order_id', { exact: true }).click()

		// A date x-axis draws a time scale. The demo orders run into 2018, and a
		// month grain keeps every month under 100 orders.
		const chart = chartOf(page)
		await expect(chart.getByText('2017')).toBeVisible()
		await expect(chart.getByText('2018')).toBeVisible()
		await expect(chart.getByText('100')).toBeVisible()
	})

	test('a user drills down from a chart into rows', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		// The chart carries a filter so that it draws one bar. Category order is
		// not stable between runs, so a chart of every status offers no bar this
		// flow could name.
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Bar',
			config: barConfig(ORDER_STATUS, {
				filters: {
					logical_operator: 'And',
					filters: [
						{
							column: { type: 'column', column_name: 'order_status' },
							operator: '=',
							value: 'canceled',
						},
					],
				},
			}),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)

		const rendered = chartOf(page)
		await expect(rendered.getByText('canceled')).toBeVisible()

		// locator: a bar is a filled `<path>`. Every other path in an echarts SVG
		// is an axis line or a split line, and those carry `fill="none"`.
		await rendered.locator('path[fill]:not([fill="none"])').click()

		// The drill-down opens the rows behind the bar. 53 of the 2,000 demo
		// orders are canceled.
		const drillDown = page.getByRole('dialog', { name: 'Drill Down' })
		await expect(drillDown.locator('tbody tr:has(td)')).toHaveCount(53)
		await expect(drillDown.getByRole('cell', { name: 'canceled' })).not.toHaveCount(0)
	})

	test('a user turns off percentages on a Funnel chart', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		// Two stages, largest first. A funnel truncates a label that outgrows
		// its bar, and it reads every share against the leading stage.
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Funnel',
			config: {
				label_column: ORDER_STATUS,
				value_column: COUNT_OF_ROWS,
				show_percentage: true,
				order_by: [{ column: { column_name: 'count_of_rows' }, direction: 'desc' }],
				limit: 2,
			},
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)

		// A funnel writes each stage's share beside its value. 1,778 of the
		// 2,000 demo orders are delivered, which leads, and 85 are shipped.
		const rendered = chartOf(page)
		await expect(rendered.getByText('1.78K (100%)')).toBeVisible()
		await expect(rendered.getByText('85 (5%)')).toBeVisible()

		const toggle = page.getByRole('switch', { name: 'Show Percentage' })
		await toggle.click()

		// The toggle drives only the label text, so the stages stay and their
		// shares go.
		await expect(rendered.getByText('1.78K', { exact: true })).toBeVisible()
		await expect(rendered.getByText('85', { exact: true })).toBeVisible()
		await expect(rendered.getByText('delivered')).toBeVisible()

		// Turning it back on brings them back. The shares live only in the
		// funnel's label closures, so nothing else about the chart changes
		// across either click.
		await toggle.click()
		await expect(rendered.getByText('1.78K (100%)')).toBeVisible()
		await expect(rendered.getByText('85 (5%)')).toBeVisible()
	})

	test('a number card shows a comparison and a sparkline', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Number',
			config: {
				number_columns: [COUNT_OF_ROWS],
				number_column_options: [],
				date_column: purchaseDate('month'),
				comparison: true,
				sparkline: true,
			},
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)

		// locator: a Number chart draws plain HTML, not echarts. Its root is the
		// page's only `@container`, and `@` needs an attribute match because it
		// is not a valid class token in a CSS selector.
		const card = page.locator('[class*="@container"]')
		// A card reads the last date in the result, and compares it against the
		// one before. The demo orders end with 74 in October 2018, against 85 in
		// September.
		await expect(card.getByText('count_of_rows')).toBeVisible()
		await expect(card.getByText('74', { exact: true })).toBeVisible()
		await expect(card.getByText('↓')).toBeVisible()
		await expect(card.getByText('-12.94%')).toBeVisible()

		// The sparkline is an echarts chart of its own, and the only one a Number
		// chart draws. It plots one filled area over the date column.
		const sparkline = chartOf(page)
		await expect(sparkline).toBeVisible()
		await expect(sparkline.locator('path[fill]:not([fill="none"])')).not.toHaveCount(0)
	})

	test('a user renames a chart while it saves and the newer name wins', async ({
		page,
		adminApi,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		const chart = await createChart(adminApi, {
			workbook: workbook.name,
			query: query.name,
			chartType: 'Bar',
			config: barConfig(ORDER_STATUS),
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/chart/${chart.name}`)
		await expect(chartOf(page).getByText('delivered')).toBeVisible()

		const hold = holdFirstWrite(page, 'Insights Chart v3')
		await hold.routed

		// locator: the workbook navbar holds a second textbox, and "Untitled
		// Workbook" carries "title" as a substring, so the match must be exact.
		const title = page.getByRole('textbox', { name: 'Title', exact: true })
		const first = `${chart.title} one`
		const second = `${chart.title} two`

		// The editor commits on Enter and saves 1.5 seconds later.
		await title.fill(first)
		await title.press('Enter')
		await hold.started

		// The second name is typed while the first write is still open.
		await title.fill(second)
		await title.press('Enter')
		hold.release()

		// The write in flight keeps the newer name instead of replacing it, and
		// a second write carries that name to the server. Two writes, no storm.
		await expect.poll(() => hold.titles).toEqual([first, second])

		await page.reload()
		await expect(page.getByRole('textbox', { name: 'Title', exact: true })).toHaveValue(second)
		await expect(page.getByRole('link', { name: second })).toBeVisible()
	})
})
