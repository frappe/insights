import { call } from 'frappe-ui'
import { computed, reactive } from 'vue'

type SessionUser = {
	email: string
	first_name: string
	last_name: string
	full_name: string
	user_image: string
	is_admin: boolean
	is_user: boolean
	can_download: boolean
	/** Whether this user may add or change Trusted code. */
	can_write_trusted_code: boolean
	locale: string
	has_desk_access?: boolean
	has_demo_data: boolean
	/** Whether the site has a workbook of its own, not one an app ships. */
	has_workbooks: boolean
	/** Whether the user used Insights 3 and has not yet closed the upgrade dialog. */
	upgraded_from_v3: boolean
	/** Whether the user owns a workbook, so the upgrade wizard explains how sharing changed. */
	owns_workbooks?: boolean
	/** Open upgrade items the user works through. */
	upgrade_item_count: number
	/** Whether the user works through every open upgrade item, not only their own. */
	is_upgrade_admin?: boolean
	/** Whether the user may open a dashboard an app ships. */
	reads_standard_dashboards?: boolean
	/** Whether the user may create the desk document Show in Desk makes for a chart. */
	can_show_in_desk?: boolean
}

// Settings of the site, not of whoever is reading it. A guest opening a public
// dashboard gets these and nothing else, so a shared chart prints its amounts
// the same way the workbook does.
type Currency = { symbol: string; symbol_on_right: boolean; number_format: string }
type SiteInfo = {
	/** Frappe's number format for a plain number, such as `#,###.##`. */
	number_format: string
	/** The day a week is counted from, as `Insights Settings` names it. */
	week_starts_on: string
	/** The date a fiscal year starts on: `Insights Settings`, else ERPNext's current Fiscal Year. */
	fiscal_year_start: string
	// stands in for a measure that names no currency column
	currency: string | null
	// starts with the site currency; each result adds its codes
	currency_symbols: Record<string, Currency>
	/** The two properties `docs/telemetry.md` puts on every event. */
	app_version: string
	entry: string
	/** Whether the site is in developer mode. Exporting a workbook to an app needs it. */
	developer_mode: boolean
}

const emptySite: SiteInfo = {
	number_format: '',
	week_starts_on: 'Monday',
	fiscal_year_start: '1995-04-01',
	currency: null,
	currency_symbols: {},
	app_version: '',
	entry: '',
	developer_mode: false,
}

const emptyUser: SessionUser = {
	email: '',
	first_name: '',
	last_name: '',
	full_name: '',
	user_image: '',
	is_admin: false,
	is_user: false,
	can_download: true,
	can_write_trusted_code: false,
	locale: 'en-US',
	has_demo_data: false,
	has_workbooks: false,
	upgraded_from_v3: false,
	upgrade_item_count: 0,
}

const session = reactive({
	user: { ...emptyUser },
	site: { ...emptySite },
	initialized: false,
	isLoggedIn: computed(() => false),
	isAuthorized: computed(() => false),
	initialize,
	fetchSessionInfo,
	fetchSiteInfo,
	login,
	logout,
	resetSession,
})

// @ts-ignore
session.isLoggedIn = computed(() => session.user.email && session.user.email !== 'Guest')
// @ts-ignore
session.isAuthorized = computed(() => session.user.is_admin || session.user.is_user)

async function initialize(force: boolean = false) {
	if (session.initialized && !force) return
	Object.assign(session.user, getSessionFromCookies())
	// the site's own settings reach a guest too, so they are fetched apart from
	// the user's, and alongside them rather than after
	await Promise.all([fetchSiteInfo(), session.isLoggedIn ? fetchSessionInfo() : null])
	session.initialized = true
}

async function fetchSessionInfo() {
	if (!session.isLoggedIn) return
	const userInfo: SessionUser = await call('insights.api.get_user_info')
	Object.assign(session.user, {
		...userInfo,
		is_admin: Boolean(userInfo.is_admin),
		is_user: Boolean(userInfo.is_user),
		has_desk_access: Boolean(userInfo.has_desk_access),
		has_demo_data: Boolean(userInfo.has_demo_data),
		has_workbooks: Boolean(userInfo.has_workbooks),
		can_download: Boolean(userInfo.can_download),
		can_write_trusted_code: Boolean(userInfo.can_write_trusted_code),
		upgraded_from_v3: Boolean(userInfo.upgraded_from_v3),
		owns_workbooks: Boolean(userInfo.owns_workbooks),
		is_upgrade_admin: Boolean(userInfo.is_upgrade_admin),
		reads_standard_dashboards: Boolean(userInfo.reads_standard_dashboards),
		can_show_in_desk: Boolean(userInfo.can_show_in_desk),
	})
}

async function fetchSiteInfo() {
	const siteInfo: SiteInfo = await call('insights.api.get_site_info')
	Object.assign(session.site, siteInfo)
}

async function login(email: string, password: string) {
	resetSession()
	const userInfo = await call('login', { usr: email, pwd: password })
	if (!userInfo) return
	Object.assign(session.user, userInfo)
	window.location.reload()
}

async function logout() {
	resetSession()
	await call('logout')
	window.location.reload()
}

function resetSession() {
	Object.assign(session.user, { ...emptyUser })
}

function getSessionFromCookies() {
	return document.cookie
		.split('; ')
		.map((c) => c.split('='))
		.reduce((acc, [key, value]) => {
			key = key === 'user_id' ? 'email' : key
			acc[key] = decodeURIComponent(value)
			return acc
		}, {} as any)
}

export default session
export type Session = typeof session
