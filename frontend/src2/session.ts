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
	country: string
	locale: string
	has_desk_access?: boolean
	has_demo_data: boolean
	fiscal_year_start: string
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
	country: '',
	locale: 'en-US',
	has_demo_data: false,
	fiscal_year_start: '01-04-2020',
}

const session = reactive({
	user: { ...emptyUser },
	initialized: false,
	isLoggedIn: computed(() => false),
	isAuthorized: computed(() => false),
	initialize,
	fetchSessionInfo,
	login,
	logout,
	resetSession,
})

// @ts-ignore
session.isLoggedIn = computed(() => session.user.email && session.user.email !== 'Guest')
// @ts-ignore
session.isAuthorized = computed(() => session.user.is_admin || session.user.is_user)

// Every surface runs this before it draws — the SPA through its router guard,
// an island through its mount shell. The in-flight request is what's shared, not
// just the finished flag: a desk page can mount several islands at once, and
// `initialized` is only set after the await, so each would ask on its own.
let pending: Promise<void> | undefined

async function initialize(force: boolean = false) {
	if (session.initialized && !force) return
	if (force) pending = undefined
	pending ??= load().catch((error) => {
		// a failed call must not leave every later caller holding the rejection
		pending = undefined
		throw error
	})
	return pending
}

async function load() {
	Object.assign(session.user, getSessionFromCookies())
	await fetchSessionInfo()
	session.initialized = true
}

async function fetchSessionInfo() {
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

// Who the browser is signed in as, straight from the cookie the server sets for
// every session. Readable before `initialize` and inside the desk island, which
// mounts a component with no SPA around it to run the session setup.
export function getCurrentUser(): string {
	return getSessionFromCookies().email || 'Guest'
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
