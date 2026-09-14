import type { Locator, Page } from '@playwright/test'
import { expect, test } from '../fixtures'
import { INSIGHTS_PATH } from '../helpers/auth'
import { createQuery, sourceOperation, uniqueTitle } from '../helpers/insights'

/**
 * locator: <thead> uses <td>, and <tbody> ends with a cell-less spacer row, so
 * role=row over-counts. `:has(td)` keeps only real data rows.
 */
function dataRows(page: Page): Locator {
	return page.locator('tbody tr:has(td)')
}

/**
 * locator: a header cell is a <td data-column-name>. The two buttons inside it
 * are icon-only and carry no accessible name, so position inside the cell is
 * the only handle. The first changes the column type, the last opens the menu.
 */
function columnMenu(page: Page, column: string): Locator {
	return page.locator(`td[data-column-name="${column}"] button`).last()
}

function columnTypeMenu(page: Page, column: string): Locator {
	return page.locator(`td[data-column-name="${column}"] button`).first()
}

/** A header cell renders its name in a contenteditable div, not in an input. */
function columnTitle(page: Page, column: string): Locator {
	return page.locator(`td[data-column-name="${column}"] [contenteditable="true"]`)
}

const ORDER_STATUS_FILTER = (status: string) => ({
	type: 'filter_group',
	logical_operator: 'And',
	filters: [
		{
			column: { type: 'column', column_name: 'order_status' },
			operator: '=',
			value: status,
		},
	],
})

test.describe('query', () => {
	// @feature query.source-table query.interface-picker
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

	// @feature query.filter query.reopen-operation
	test('a user adds a filter and the row count falls', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()
		await expect(dataRows(page)).toHaveCount(100)

		await page.getByRole('button', { name: 'Add Operation' }).click()
		await page.getByRole('button', { name: 'Filter Rows' }).click()
		await page.getByRole('button', { name: 'Add Filter' }).click()

		await page.getByRole('combobox', { name: 'Column' }).fill('order_status')
		await page.getByRole('option', { name: 'order_status' }).click()

		// The default operator for a text column is "is", which offers the
		// distinct values of the column.
		await page.getByRole('button', { name: 'Value' }).click()
		await page.getByRole('option', { name: 'canceled' }).click()
		await page.keyboard.press('Escape')

		await page.getByRole('button', { name: 'Apply Filters' }).click()

		// 53 of the 2,000 demo orders are canceled.
		await expect(dataRows(page)).toHaveCount(53)
		await expect(page.getByRole('cell', { name: 'delivered', exact: true })).toHaveCount(0)

		// A double-click on the step reopens its editor, filled with what was
		// saved: the value control reads `canceled` rather than its placeholder.
		// locator: an operation row is a plain div. Its own text is the only
		// handle, and the same two words name the Filter step alone.
		const filterStep = page
			.locator('div.group')
			.filter({ hasText: 'Filter' })
			.filter({ hasText: 'order_status' })
		await filterStep.dblclick()

		const reopened = page.getByRole('dialog')
		await reopened.getByRole('button', { name: 'canceled' }).click()
		await page.getByRole('option', { name: 'shipped' }).click()
		// The value list is a multi-select, so the rule keeps `canceled` until it
		// is picked off again.
		await page.getByRole('option', { name: 'canceled' }).click()
		await page.keyboard.press('Escape')
		await reopened.getByRole('button', { name: 'Apply Filters' }).click()

		// 85 of the 2,000 demo orders are shipped. The pipeline still holds one
		// Filter step, because the editor changed the step it was opened on.
		await expect(dataRows(page)).toHaveCount(85)
		await expect(page.getByRole('cell', { name: 'canceled', exact: true })).toHaveCount(0)
		await expect(page.getByRole('cell', { name: 'shipped', exact: true })).not.toHaveCount(0)
		await expect(filterStep).toHaveCount(1)
	})

	// @feature query.summarize query.summarize-grain
	test('a user adds a summarize and the grain changes', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(dataRows(page)).toHaveCount(100)

		await page.getByRole('button', { name: 'Add Operation' }).click()
		await page.getByRole('button', { name: 'Group & Summarize' }).click()

		// The dialog holds a Group By pane and an Aggregate pane. Both open with a
		// picker reading "Select a column", and only their order tells them apart.
		await page.getByRole('button', { name: 'Select a column' }).first().click()
		await page.getByRole('option', { name: 'order_status' }).click()

		await page.getByRole('button', { name: 'Select a column' }).first().click()
		await page.getByText('Count of...', { exact: true }).click()
		await page.getByPlaceholder('Search...').fill('order_id')
		// locator: the column options are plain divs, and the same name also labels
		// a header cell behind the dialog. reka portals the popover to <body> and
		// marks it, so the search box inside it names the popover and nothing else.
		await page
			.locator('[data-reka-popper-content-wrapper]', {
				has: page.getByPlaceholder('Search...'),
			})
			.getByText('order_id', { exact: true })
			.click()

		await page.getByRole('button', { name: 'Done' }).click()

		// The six order statuses replace the 2,000 rows.
		await expect(dataRows(page)).toHaveCount(6)
		await expect(page.getByRole('cell', { name: 'count_of_order_id' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'delivered', exact: true })).toBeVisible()
		await expect(page.getByRole('cell', { name: '1,778' })).toBeVisible()
	})

	// @feature query.join
	test('a user joins a second table and sees its columns', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'customer_id' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'customer_city' })).toHaveCount(0)

		await page.getByRole('button', { name: 'Add Operation' }).click()
		await page.getByRole('button', { name: 'Join Table' }).click()

		await page.getByPlaceholder('Table').fill('customers')
		await page.getByRole('option', { name: 'customers' }).click()

		// The declared foreign key fills both join columns, so the flow only picks
		// the columns to add.
		await page.getByRole('button', { name: 'Columns' }).click()
		await page.getByRole('option', { name: 'customer_city' }).click()
		await page.keyboard.press('Escape')

		await page.getByRole('button', { name: 'Confirm' }).click()

		await expect(page.getByRole('cell', { name: 'customer_city' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'sao paulo' })).not.toHaveCount(0)
		// Every order has a customer, so the join keeps the row count.
		await expect(dataRows(page)).toHaveCount(100)
	})

	// @feature query.mutate query.mutate-inline
	test('a user adds a mutate with an expression and sees the new column', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		await page.getByRole('button', { name: 'Add Operation' }).click()
		await page.getByRole('button', { name: 'Add New Column' }).click()

		// locator: the expression editor is CodeMirror, and its input is a
		// contenteditable div. The dialog's Column Name field carries the same
		// textbox role, so only the editor class separates the two.
		await page.locator('.cm-content').fill('order_status.upper()')
		await page.getByLabel('Column Name').fill('shout')
		await page.getByRole('button', { name: 'Confirm' }).click()

		await expect(page.getByRole('cell', { name: 'shout' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'DELIVERED' })).not.toHaveCount(0)

		// The empty column at the end of the grid is the second way in. It takes
		// an expression and nothing else, so the column it writes is named
		// `new_column` and typed from the expression.
		// locator: the `+` that opens it, and the tick that confirms it, are
		// icon-only Buttons that pass no label. The lucide class each icon
		// carries is the only name they have, and the header row is what keeps
		// the match off the toolbar's own `+`.
		await page.locator('thead button:has(svg.lucide-plus)').click()
		// locator: the inline expression editor is CodeMirror. Its own class is
		// what separates it from the editor the dialog above opened.
		await page.locator('.inline-expression .cm-content').fill('order_status.length()')
		await page.locator('thead button:has(svg.lucide-check)').click()

		await expect(page.getByRole('cell', { name: 'new_column' })).toBeVisible()
		// A mutate adds a column and touches no row, so the page still holds 100.
		await expect(dataRows(page)).toHaveCount(100)
		// locator: an operation row is a plain div carrying its own words. Both
		// calculated columns are now steps of the pipeline.
		await expect(page.locator('div.group').filter({ hasText: 'Calculate' })).toHaveCount(2)
	})

	// @feature query.step-back
	test('a user steps back to an earlier operation and the results rewind', async ({
		page,
		adminApi,
		demoDataSource,
		workbook,
	}) => {
		const query = await createQuery(adminApi, {
			workbook: workbook.name,
			dataSource: demoDataSource,
			operations: [sourceOperation('orders'), ORDER_STATUS_FILTER('canceled')],
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(dataRows(page)).toHaveCount(53)

		// The operations list names the source step "Select orders table".
		await page.getByText('Select', { exact: true }).click()

		await expect(dataRows(page)).toHaveCount(100)
		await expect(page.getByRole('cell', { name: 'delivered' })).not.toHaveCount(0)
	})

	// @feature query.remove-operation
	test('a user removes an operation mid-pipeline', async ({
		page,
		adminApi,
		demoDataSource,
		workbook,
	}) => {
		const query = await createQuery(adminApi, {
			workbook: workbook.name,
			dataSource: demoDataSource,
			operations: [
				sourceOperation('orders'),
				ORDER_STATUS_FILTER('canceled'),
				{
					type: 'order_by',
					column: { type: 'column', column_name: 'order_id' },
					direction: 'asc',
				},
			],
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(dataRows(page)).toHaveCount(53)

		// locator: an operation row is a plain div, and the X that removes it is an
		// icon-only Button with no accessible name. The row's own text is the only
		// handle.
		const filterRow = page
			.locator('div.group')
			.filter({ hasText: 'Filter' })
			.filter({ hasText: 'order_status' })
		await filterRow.getByRole('button').click()

		// The sort survives, so the first page starts at the first order again.
		await expect(dataRows(page)).toHaveCount(100)
		await expect(page.getByRole('cell', { name: 'ORD-00001' })).toBeVisible()
	})

	/**
	 * Renaming and removing are two flows, not one.
	 *
	 * Each one edits the query, and each edit redraws the results twice: once
	 * when the new rows arrive, once when the save answer replaces the document.
	 * A second edit made across either redraw is lost, and an open column menu
	 * closes under it. See "Never wait in the middle of an edit" in AGENTS.md.
	 * One edit per flow, on a page that has gone quiet, has neither problem.
	 */
	// @feature query.rename-column
	test('a user renames a column', async ({ page, demoDataSource, workbookWithQuery }) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		const title = columnTitle(page, 'order_status')
		await title.fill('status')
		await title.press('Enter')

		await expect(page.getByRole('cell', { name: 'status', exact: true })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'order_status' })).toHaveCount(0)
	})

	// @feature query.remove-column
	test('a user removes a column', async ({ page, demoDataSource, workbookWithQuery }) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'order_approved_at' })).toBeVisible()

		await columnMenu(page, 'order_approved_at').click()
		await page.getByRole('button', { name: 'Remove', exact: true }).click()

		// Wait on the column that survives, not on the one that goes. Removing a
		// column re-runs the query, and `toHaveCount(0)` passes on the empty
		// table it renders meanwhile — so the negative assertion means nothing
		// until the table is back. A two-core runner needs longer than the
		// 15 second default to re-execute.
		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible({
			timeout: 45_000,
		})
		await expect(page.getByRole('cell', { name: 'order_approved_at' })).toHaveCount(0)
	})

	// @feature query.cast-column
	test('a user casts a column type', async ({ page, adminApi, demoDataSource, workbook }) => {
		const query = await createQuery(adminApi, {
			workbook: workbook.name,
			dataSource: demoDataSource,
			table: 'orderitems',
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'shipping_limit_date' })).toBeVisible()
		// `shipping_limit_date` is the only column in orderitems that prints a
		// time, and no shipping time in the demo data falls on midnight.
		await expect(page.getByRole('cell', { name: /00:00:00/ })).toHaveCount(0)

		await columnTypeMenu(page, 'shipping_limit_date').click()
		await page.getByRole('button', { name: 'Date', exact: true }).click()

		await expect(page.getByText('Convert')).toBeVisible()
		// A Date still prints a time, and the cast drops that time to midnight.
		await expect(page.getByRole('cell', { name: /00:00:00/ })).toHaveCount(100)
		await expect(dataRows(page)).toHaveCount(100)
	})

	// @feature query.order-by
	test('a user sorts by a column', async ({ page, demoDataSource, workbookWithQuery }) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'ORD-00001' })).toBeVisible()

		await columnMenu(page, 'order_id').click()
		await page.getByRole('button', { name: 'Descending' }).click()

		// The 2,000 order ids run from ORD-00001 to ORD-02000.
		await expect(page.getByRole('cell', { name: 'ORD-02000' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'ORD-00001' })).toHaveCount(0)
	})

	// @feature query.filter-relative-date
	test('a user filters on a date with the relative date picker', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(dataRows(page)).toHaveCount(100)

		await page.getByRole('button', { name: 'Add Operation' }).click()
		await page.getByRole('button', { name: 'Filter Rows' }).click()
		await page.getByRole('button', { name: 'Add Filter' }).click()

		await page.getByRole('combobox', { name: 'Column' }).fill('order_purchase_timestamp')
		await page.getByRole('option', { name: 'order_purchase_timestamp' }).click()

		// locator: the operator control is a listbox, not a native select, and it
		// carries no label. The row wraps it in a div with a stable id.
		await page.locator('#operator').getByRole('combobox').click()
		await page.getByRole('option', { name: 'within' }).click()

		await page.getByPlaceholder('Relative Date').click()
		// The picker opens on "Last 1 Day". Its select trigger takes no accessible
		// name from its content, so the value it shows is the only handle.
		await page.getByRole('combobox').filter({ hasText: 'Day' }).click()
		await page.getByRole('option', { name: 'Year', exact: true }).click()
		await page.getByRole('button', { name: 'Done' }).click()

		await page.getByRole('button', { name: 'Apply Filters' }).click()

		// The demo orders stop in 2018, so the last year holds none of them. A
		// result with no rows draws no table at all, headers included, so what
		// the editor shows is the empty state and the count behind it.
		await expect(dataRows(page)).toHaveCount(0)
		await expect(page.getByText('No data to display.')).toBeVisible()
		await expect(page.getByText('Showing 0 rows')).toBeVisible()
		await expect(page.getByText('Filter', { exact: true })).toBeVisible()
	})

	// @feature query.native-sql query.interface-picker query.native-sql-schema-explorer
	test('a user writes a native SQL query and runs it', async ({
		page,
		demoDataSource,
		workbook,
	}) => {
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)

		// The three interface cards are clickable divs with no role and no label.
		await page.getByText('SQL Editor').click()

		await page.getByRole('button', { name: 'Select a data source' }).click()
		await page.getByRole('option', { name: 'Demo Data' }).click()

		// The schema explorer beside the editor writes names into it. A table name
		// is a button of its own; the row around it is what opens the table.
		// locator: the SQL editor is CodeMirror, and its input is a contenteditable
		// div. The Query Title field carries the same textbox role, so only the
		// editor class separates the two.
		const editor = page.locator('.cm-content')
		await page.getByPlaceholder('Search tables and columns...').fill('orders')
		await page.getByRole('button', { name: 'orders', exact: true }).click()
		await expect(editor).toContainText('`orders`')

		// locator: the row that expands a table is a plain div, and the name
		// inside it stops the click before it reaches the row. The row is named
		// by the button it holds, and the chevron carries only its lucide class.
		await page.locator('div:has(> button:text-is("orders"))').locator('svg').first().click()
		// A column button reads its name and then its type, so the match is on
		// the name it starts with.
		await page.getByRole('button', { name: /^order_status/ }).click()
		await expect(editor).toContainText('`order_status`')

		await editor.fill('select order_status from orders group by order_status')
		await page.getByRole('button', { name: 'Execute' }).click()

		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'delivered', exact: true })).toBeVisible()
		await expect(dataRows(page)).toHaveCount(6)
	})

	// @feature query.pivot-wider
	test('a user pivots wider', async ({ page, adminApi, demoDataSource, workbook }) => {
		const query = await createQuery(adminApi, {
			workbook: workbook.name,
			dataSource: demoDataSource,
			table: 'orderpayments',
		})
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'payment_type' })).toBeVisible()

		await page.getByRole('button', { name: 'Add Operation' }).click()
		await page.getByRole('button', { name: 'Pivot' }).click()

		// The dialog holds a Rows, a Columns and a Values pane. All three open with
		// a picker reading "Select a column", and only their order tells them apart.
		await page.getByRole('button', { name: 'Select a column' }).first().click()
		await page.getByRole('option', { name: 'payment_installments' }).click()

		await page.getByRole('button', { name: 'Select a column' }).first().click()
		await page.getByRole('option', { name: 'payment_type' }).click()

		await page.getByRole('button', { name: 'Select a column' }).first().click()
		await page.getByText('Count of...', { exact: true }).click()
		await page.getByPlaceholder('Search...').fill('order_id')
		// locator: the column options are plain divs, and the same name also labels
		// a header cell behind the dialog. reka portals the popover to <body> and
		// marks it, so the search box inside it names the popover and nothing else.
		await page
			.locator('[data-reka-popper-content-wrapper]', {
				has: page.getByPlaceholder('Search...'),
			})
			.getByText('order_id', { exact: true })
			.click()

		await page.getByRole('button', { name: 'Done' }).click()

		// The four payment types become columns, one row per installment count.
		// The row count settles first, because until it does the payment type is
		// still a value in many body cells rather than one header cell.
		await expect(dataRows(page)).toHaveCount(12)
		await expect(page.getByRole('cell', { name: 'credit_card' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'boleto' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'debit_card' })).toBeVisible()
		await expect(page.getByRole('cell', { name: 'voucher' })).toBeVisible()
	})

	// @feature query.union
	test('a user unions two queries', async ({ page, adminApi, demoDataSource, workbook }) => {
		const unavailable = await createQuery(adminApi, {
			workbook: workbook.name,
			title: uniqueTitle('Unavailable Orders'),
			dataSource: demoDataSource,
			operations: [sourceOperation('orders'), ORDER_STATUS_FILTER('unavailable')],
		})
		const processing = await createQuery(adminApi, {
			workbook: workbook.name,
			title: uniqueTitle('Processing Orders'),
			dataSource: demoDataSource,
			operations: [sourceOperation('orders'), ORDER_STATUS_FILTER('processing')],
		})

		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${unavailable.name}`)

		// 16 orders are unavailable and 33 are processing.
		await expect(dataRows(page)).toHaveCount(16)

		await page.getByRole('button', { name: 'Add Operation' }).click()
		await page.getByRole('button', { name: 'Append Table' }).click()

		await page.getByPlaceholder('Table').fill(processing.title)
		await page.getByRole('option', { name: processing.title }).click()
		await page.getByRole('button', { name: 'Confirm' }).click()

		await expect(dataRows(page)).toHaveCount(49)
		await expect(page.getByRole('cell', { name: 'processing' })).not.toHaveCount(0)
		await expect(page.getByRole('cell', { name: 'unavailable' })).not.toHaveCount(0)
	})

	// @feature query.view-sql
	test('a user opens View SQL and sees compiled SQL', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()

		// locator: the toolbar's overflow menu is an icon-only Button with no
		// accessible name. The Execute button beside it is the only stable anchor.
		await page
			.locator('div:has(button[aria-label="Execute"]) > button[aria-haspopup="menu"]')
			.click()
		await page.getByRole('menuitem', { name: 'View SQL' }).click()

		const dialog = page.getByRole('dialog')
		await expect(dialog.getByText('Generated SQL')).toBeVisible()
		// locator: CodeMirror splits the statement across one span per token, so
		// the editor body is the only node that holds the whole text.
		await expect(dialog.locator('.cm-content')).toContainText('orders')
		await expect(dialog.locator('.cm-content')).toContainText(/select/i)
	})

	// @feature query.filter-from-column-header
	test('a user filters from a column header and the rows narrow', async ({
		page,
		demoDataSource,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await page.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)

		await expect(page.getByRole('cell', { name: 'order_status' })).toBeVisible()
		await expect(dataRows(page)).toHaveCount(100)

		await columnMenu(page, 'order_status').click()
		await page.getByRole('button', { name: 'Filter', exact: true }).click()

		// locator: the filter panel is portaled to <body> by reka and marked only
		// on its wrapper, so nothing inside it is reachable from the trigger. Its
		// own value search is what tells it from the menu it opened over.
		const panel = page.locator('[data-reka-popper-content-wrapper]', {
			has: page.getByPlaceholder('Search'),
		})
		// The operator opens on "is", which lists the distinct values of the
		// column. A value is a plain row, not an option.
		await panel.getByText('canceled', { exact: true }).click()
		// locator: the panel's confirm is icon-only and passes no label, so
		// frappe-ui renders it with no accessible name. Its lucide icon class is
		// the name.
		await panel.locator('button:has(span.lucide-check)').click()

		// 53 of the 2,000 demo orders are canceled, and the pipeline gained the
		// Filter step the header wrote.
		await expect(dataRows(page)).toHaveCount(53)
		await expect(page.getByRole('cell', { name: 'delivered', exact: true })).toHaveCount(0)
		await expect(
			page
				.locator('div.group')
				.filter({ hasText: 'Filter' })
				.filter({ hasText: 'order_status' }),
		).toHaveCount(1)
	})
})
