import { test as teardown } from '@playwright/test'
import { restoreSiteState } from '../helpers/site-state'

/**
 * Put back the site-wide settings the setup project changed.
 *
 * Playwright runs this after every project that depends on `setup` finishes.
 */
teardown('restore site settings', async ({ browser }) => {
	await restoreSiteState(browser)
})
