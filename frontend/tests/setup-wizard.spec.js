import { expect, test } from '@playwright/test'

const login = async () => {
	await frappe.call('login', {
		usr: 'Administrator',
		pwd: 'frappe',
	})
}

test('setup-wizard', async ({ page }) => {
	await page.goto('http://frappe-insights:8000/')
	await page.evaluate(login)
	await page.goto('http://frappe-insights:8000/app/setup-wizard/0')
	await page
		.getByRole('listitem')
		.filter({ hasText: /^English$/ })
		.click()
	await page.getByPlaceholder('Select Country').click()
	await page.getByPlaceholder('Select Country').fill('india')
	await page
		.getByRole('listitem')
		.filter({ hasText: /^India$/ })
		.click()
	await page.getByRole('button', { name: 'Next' }).click()
	await page.getByRole('textbox').first().fill('Test')
	await page.getByRole('textbox').nth(1).click()
	await page.getByRole('textbox').nth(1).fill('test@test.com')
	await page.locator('input[type="password"]').click()
	await page.locator('input[type="password"]').fill('test')
	await page.getByRole('button', { name: 'Complete Setup' }).click()
	await page.waitForFunction(() => window.location.pathname.includes('/insights'))
	expect(page.url()).toContain('/insights')
})
