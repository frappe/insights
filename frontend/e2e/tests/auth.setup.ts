import { test as setup } from '@playwright/test'
import { CREDENTIALS, captureAuthState, readCsrfToken } from '../helpers/auth'
import { createFrappeApi, type FrappeApi } from '../helpers/frappe'
import { setTeamPermissions } from '../helpers/insights'
import { saveSiteState } from '../helpers/site-state'
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
	await markUpgradeSeen(adminApi)

	// Team permissions are on for the whole run. A test that flipped them would
	// flip them for every worker beside it, because the suite runs fully
	// parallel against one site. The admin bypasses team checks, so admin flows
	// read the same either way, and the viewer belongs to no team, which is the
	// state the denial flow needs.
	//
	// The setting is site-wide, so record it first. The teardown project puts
	// the old value back when the run ends.
	await saveSiteState(adminApi)
	await setTeamPermissions(adminApi, true)

	await adminContext.close()

	const viewerContext = await captureAuthState(browser, 'viewer')
	await markUpgradeSeen(createFrappeApi(viewerContext.request, readCsrfToken('viewer')))
	await viewerContext.close()
})

/**
 * The Insights v3.50 welcome dialog opens over every page for a user marked as a
 * user of an earlier release, and a test site that once migrated from one marks
 * them. No flow here is about the upgrade, so the run starts past it.
 */
async function markUpgradeSeen(api: FrappeApi): Promise<void> {
	await api.callMethod('insights.api.upgrade.mark_upgrade_seen')
}
