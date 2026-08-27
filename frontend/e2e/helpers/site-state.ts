import type { Browser } from '@playwright/test'
import * as fs from 'node:fs'
import { SITE_STATE_PATH, readCsrfToken, storageStatePath } from './auth'
import { createFrappeApi, type FrappeApi } from './frappe'
import { getTeamPermissions, setTeamPermissions } from './insights'

/**
 * The site-wide settings a run changes, and the way back.
 *
 * The suite shares one site with whoever owns it. `enable_permissions` is on
 * for the whole run, and a developer who loses it hides every Data Source from
 * every Insights User until someone finds the setting again.
 */
export type SiteState = { enable_permissions: boolean }

/** Record what the site holds now. The setup project calls this before it writes. */
export async function saveSiteState(api: FrappeApi): Promise<void> {
	// The first record wins. A run that dies before its teardown leaves the file
	// behind and leaves the site turned on, so a second record would write the
	// value this suite set and lose the developer's own for good.
	if (fs.existsSync(SITE_STATE_PATH)) return

	const state: SiteState = { enable_permissions: await getTeamPermissions(api) }
	fs.writeFileSync(SITE_STATE_PATH, JSON.stringify(state))
}

/** Put back what `saveSiteState` recorded. Does nothing when it never ran. */
export async function restoreSiteState(browser: Browser): Promise<void> {
	if (!fs.existsSync(SITE_STATE_PATH)) return

	const state = JSON.parse(fs.readFileSync(SITE_STATE_PATH, 'utf-8')) as SiteState

	// The admin session the setup project saved, reused rather than a new login.
	const context = await browser.newContext({ storageState: storageStatePath('admin') })
	const api = createFrappeApi(context.request, readCsrfToken('admin'))
	await setTeamPermissions(api, Boolean(state.enable_permissions))
	await context.close()

	fs.rmSync(SITE_STATE_PATH)
}
