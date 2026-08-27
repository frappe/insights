import { test as setup } from '@playwright/test'
import { CREDENTIALS, captureAuthState, readCsrfToken } from '../helpers/auth'
import { createFrappeApi } from '../helpers/frappe'
import { setTeamPermissions } from '../helpers/insights'
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

	// Team permissions are off in the shape the rest of the suite expects, and
	// one permissions flow turns them on for the length of a single test. A run
	// killed inside that test leaves them on, and every later run then fails for
	// a reason no test states. Start from the known side of the switch.
	await setTeamPermissions(adminApi, false)

	await adminContext.close()

	const viewerContext = await captureAuthState(browser, 'viewer')
	await viewerContext.close()
})
