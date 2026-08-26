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
	locale: string
	has_desk_access?: boolean
	has_demo_data: boolean
	fiscal_year_start: string
}

// Settings of the site, not of whoever is reading it. A guest opening a public
// dashboard gets these and nothing else, so a shared chart prints its amounts
// the same way the workbook does.
type SiteInfo = {
	country: string
	currency: string | null
	currency_symbol: string
	currency_symbol_on_right: boolean
}

const emptySite: SiteInfo = {
	country: '',
	currency: null,
	currency_symbol: '',
	currency_symbol_on_right: false,
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
	locale: 'en-US',
	has_demo_data: false,
	fiscal_year_start: '01-04-2020',
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
		can_download: Boolean(userInfo.can_download),
	})
}

async function fetchSiteInfo() {
	const siteInfo: SiteInfo = await call('insights.api.get_site_info')
	Object.assign(session.site, {
		...siteInfo,
		currency_symbol_on_right: Boolean(siteInfo.currency_symbol_on_right),
	})
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
