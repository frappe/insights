import { expect, test } from '../fixtures'
import { CREDENTIALS, INSIGHTS_PATH } from '../helpers/auth'

/**
 * The one flow that starts signed out.
 *
 * Insights hands a visitor with no session to the site's own login page rather
 * than drawing one of its own: the router's guard sets `window.location` to
 * `/login` outside a dev build, so the app's `Login.vue` never renders in the
 * build this suite runs against. The page under test here is therefore the site
 * login page, which is what a user of Insights actually meets.
 */
test.describe('settings', () => {
	// @feature settings.login settings.log-out
	test('a user logs in, is told when the password is wrong, and logs out', async ({
		guestPage,
	}) => {
		await guestPage.goto(INSIGHTS_PATH)

		// No session, so the app sends the visitor to the login page.
		await expect(guestPage).toHaveURL(/\/login/)

		// locator: the page draws a sign-up and a forgot-password section beside
		// the sign-in one, each with its own Email field, and all three are in the
		// DOM at once. The sign-in form's own class is what names its fields.
		const form = guestPage.locator('form.form-login')
		await expect(form.getByLabel('Email')).toBeVisible()

		await form.getByLabel('Email').fill(CREDENTIALS.admin.usr)
		await form.getByLabel('Password').fill('not-the-password')
		await form.getByRole('button', { name: 'Continue' }).click()

		// A refused login says so on the page and leaves the visitor on it.
		await expect(form.getByText(/invalid/i)).toBeVisible()
		await expect(guestPage).toHaveURL(/\/login/)

		await form.getByLabel('Password').fill(CREDENTIALS.admin.pwd)
		await form.getByRole('button', { name: 'Continue' }).click()

		// A login lands on the signed-in home the site names, which is not the
		// login page. Insights is then reachable, and its home is the dashboard
		// list.
		await expect(guestPage).not.toHaveURL(/\/login/)
		await guestPage.goto(INSIGHTS_PATH)
		await expect(guestPage).toHaveURL(/\/dashboards$/)

		// The sidebar's user menu carries the app's name and the signed-in user's.
		const userMenu = guestPage.getByRole('button', { name: /Insights/ })
		await expect(userMenu).toBeVisible()
		await userMenu.click()
		await guestPage.getByRole('menuitem', { name: 'Log out' }).click()

		const confirm = guestPage.getByRole('dialog', { name: 'Log out' })
		await expect(confirm.getByText('Are you sure you want to log out?')).toBeVisible()
		await confirm.getByRole('button', { name: 'Confirm' }).click()

		// Logging out drops the session and reloads, and the app has nowhere to
		// send a visitor without one but the login page.
		await expect(guestPage).toHaveURL(/\/login/)
		await expect(guestPage.locator('form.form-login').getByLabel('Email')).toBeVisible()
	})
})
