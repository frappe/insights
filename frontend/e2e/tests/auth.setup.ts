import { test as setup } from '@playwright/test'
import { CREDENTIALS, captureAuthState, readCsrfToken } from '../helpers/auth'
import { createFrappeApi } from '../helpers/frappe'
import { ensureInsightsUser } from '../helpers/users'

/**
 * Log both roles in once per run and save their state under `e2e/.auth/`.
 *
 * One test, not two, because the viewer account does not exist until the admin
 * session creates it. Playwright gives no ordering between tests in a file.
 */
setup('authenticate', async ({ browser }) => {
	const adminContext = await captureAuthState(browser, 'admin')
	const adminApi = createFrappeApi(adminContext.request, readCsrfToken('admin'))
	await ensureInsightsUser(adminApi, CREDENTIALS.viewer)
	await adminContext.close()

	const viewerContext = await captureAuthState(browser, 'viewer')
	await viewerContext.close()
})
