import { test, expect } from '@playwright/test'

test('test', async ({ page }) => {
	await page.goto('http://frappe-insights:8000/login')
	await page.getByPlaceholder('jane@example.com').click()
	await page.getByPlaceholder('jane@example.com').fill('Administrator')
	await page.getByPlaceholder('jane@example.com').press('Tab')
	await page.getByPlaceholder('•••••').fill('frappe')
	await page.getByRole('button', { name: 'Login' }).click()
})
