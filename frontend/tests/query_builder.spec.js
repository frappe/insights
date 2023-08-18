import { test } from '@playwright/test'

const login = async () => {
	await frappe.call('login', {
		usr: 'frappe@example.com',
		pwd: 'frappe',
	})
}

test('visual_sql', async ({ page }) => {
	await page.goto('http://frappe-insights:8000/')
	await page.evaluate(login)
	await page.goto('http://frappe-insights:8000/insights')
	await page.locator('a').filter({ hasText: 'Query' }).click()
	await page.getByRole('button', { name: 'New Query' }).click()
	await page
		.locator('div')
		.filter({ hasText: /^VisualCreate a query using the visual interface$/ })
		.first()
		.click()
	await page
		.locator('div')
		.filter({ hasText: /^Pick starting data$/ })
		.nth(2)
		.click()
	await page
		.locator('div')
		.filter({ hasText: /^Demo Data$/ })
		.nth(1)
		.click()
	await page
		.locator('div')
		.filter({ hasText: /^Orders$/ })
		.first()
		.click()
	await page
		.locator('div')
		.filter({ hasText: /^Combine$/ })
		.click()
	await page.locator('div:nth-child(3) > div > div > .contenteditable').click()
	await page.getByRole('option', { name: 'Orderitems orderitems' }).click()
	await page
		.locator('div')
		.filter({ hasText: /^Combine$/ })
		.nth(1)
		.click()
	await page.locator('div:nth-child(3) > .ml-2\\.5 > div > div > .contenteditable').click()
	await page.getByRole('option', { name: 'Orders' }).locator('div').first().click()
	await page
		.locator('div:nth-child(3) > .ml-2\\.5 > div:nth-child(3) > div > div > .contenteditable')
		.click()
	await page.getByRole('option', { name: 'Customers customers' }).click()
	await page
		.locator('div')
		.filter({ hasText: /^Summarise$/ })
		.click()
	await page.locator('.ml-2\\.5 > div > div > div > div > div > .contenteditable').click()
	await page.getByRole('option', { name: 'Sum of' }).click()
	await page.locator('.ml-2\\.5 > div > div > div > div:nth-child(2) > .flex').click()
	await page.getByText('Priceprice').nth(1).click()
	await page.locator('.pl-7 > .group > .ml-2\\.5 > div > div > div > div > .flex').click()
	await page
		.locator(
			'div:nth-child(30) > div > .min-w-\\[12rem\\] > .mt-1 > div > div:nth-child(3) > .flex'
		)
		.first()
		.click()
	await page
		.locator('div')
		.filter({ hasText: /^Sort$/ })
		.click()
	await page
		.locator('div')
		.filter({ hasText: /^Column$/ })
		.nth(1)
		.click()
	await page.getByText('Priceprice').nth(3).click()
	await page.locator('div:nth-child(3) > div > .contenteditable').click()
	await page.getByRole('option', { name: 'Descending' }).click()
	await page
		.locator('div')
		.filter({ hasText: /^Limit$/ })
		.click()
	await page.getByRole('button', { name: 'Execute' }).click()
})
