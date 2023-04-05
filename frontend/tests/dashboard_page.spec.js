import { expect, test } from '@playwright/test'

const login = async () => {
	await frappe.call('login', {
		usr: 'frappe@example.com',
		pwd: 'frappe',
	})
}

test('dashboard_page', async ({ page }) => {
	await page.goto('http://frappe-insights:8000/')
	await page.evaluate(login)
	await page.goto('http://frappe-insights:8000/insights')
	expect(page.getByText('Dashboards')).toBeTruthy()
})
