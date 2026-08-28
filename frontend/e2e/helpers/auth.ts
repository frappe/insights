import type { Browser, BrowserContext, Page } from '@playwright/test'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'

/** The two roles the suite logs in as. */
export type Role = 'admin' | 'viewer'

export type Credentials = { usr: string; pwd: string }

/** The route the Insights app is mounted on. Matches `insights_path` in hooks.py. */
export const INSIGHTS_PATH = process.env.INSIGHTS_PATH || '/insights'

/**
 * The viewer is an Insights User with no admin rights. Insights invites people
 * as Website Users, so the fixture user matches that shape and not a System
 * User.
 */
export const VIEWER_EMAIL = process.env.E2E_VIEWER_USER || 'e2e-viewer@example.com'

export const CREDENTIALS: Record<Role, Credentials> = {
	admin: {
		usr: process.env.E2E_ADMIN_USER || 'administrator',
		pwd: process.env.E2E_ADMIN_PASSWORD || 'frappe',
	},
	viewer: {
		usr: VIEWER_EMAIL,
		pwd: process.env.E2E_VIEWER_PASSWORD || 'e2e-viewer-secret',
	},
}

// Resolved from this file, not from the working directory, because Playwright
// resolves a relative path against `process.cwd()` and the suite may be run
// from either the repo root or `frontend/`.
const AUTH_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '.auth')

export function storageStatePath(role: Role): string {
	return path.join(AUTH_DIR, `${role}.json`)
}

/**
 * Where the setup project parks a site setting it turned on.
 *
 * Setup and teardown run in separate processes, so the old value travels
 * through a file beside the saved sessions.
 */
export const SITE_STATE_PATH = path.join(AUTH_DIR, 'site-state.json')

function csrfPath(role: Role): string {
	return path.join(AUTH_DIR, `${role}.csrf.json`)
}

/** Read the CSRF token the setup project saved for a role. */
export function readCsrfToken(role: Role): string {
	const file = csrfPath(role)
	if (!fs.existsSync(file)) {
		throw new Error(`No CSRF token for ${role}. Did the setup project run? Expected ${file}`)
	}
	return JSON.parse(fs.readFileSync(file, 'utf-8')).csrf_token
}

/**
 * Log in over the API and save the session and its CSRF token.
 *
 * A Frappe session carries no CSRF token until a page asks for one, and every
 * later write is then checked against it. Loading the Insights page is what
 * mints the token, and the app's page renderer puts it on `window.csrf_token`.
 * A run that skipped this step would write fine until the first page load and
 * fail with an opaque 417 after it.
 */
export async function captureAuthState(browser: Browser, role: Role): Promise<BrowserContext> {
	fs.mkdirSync(AUTH_DIR, { recursive: true })

	const context = await browser.newContext()
	const page = await context.newPage()

	await login(page, CREDENTIALS[role])

	await page.goto(INSIGHTS_PATH)
	// The only wait in the suite that is not tied to a visible element. Nothing
	// on the page reports that `window.csrf_token` is set, and this runs once per
	// run in the setup project, never inside a flow test.
	// eslint-disable-next-line playwright/no-networkidle
	await page.waitForLoadState('networkidle')
	const csrfToken = await page.evaluate(
		() => (window as unknown as { csrf_token?: string }).csrf_token,
	)
	if (!csrfToken) {
		throw new Error(`No csrf_token on ${INSIGHTS_PATH} for ${role}. Is the frontend built?`)
	}

	fs.writeFileSync(csrfPath(role), JSON.stringify({ csrf_token: csrfToken }))
	await context.storageState({ path: storageStatePath(role) })

	await page.close()
	return context
}

/** Log in through the API. The UI login flow is not under test here. */
export async function login(page: Page, credentials: Credentials): Promise<void> {
	const response = await page.request.post('/api/method/login', { form: credentials })
	if (!response.ok()) {
		throw new Error(`Login as ${credentials.usr} failed: ${await response.text()}`)
	}

	const logged = await page.request.get('/api/method/frappe.auth.get_logged_user')
	const user = (await logged.json()).message
	if (!user || user === 'Guest') {
		throw new Error(`Login as ${credentials.usr} left the session as Guest`)
	}
}
