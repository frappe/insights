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
	country: string
	locale: string
	is_v2_instance: boolean
	default_version: 'v3' | 'v2' | ''
}

const emptyUser: SessionUser = {
	email: '',
	first_name: '',
	last_name: '',
	full_name: '',
	user_image: '',
	is_admin: false,
	is_user: false,
	country: '',
	locale: 'en-US',
	is_v2_instance: false,
	default_version: '',
}

const session = reactive({
	user: { ...emptyUser },
	initialized: false,
	isLoggedIn: computed(() => false),
	isAuthorized: computed(() => false),
	initialize,
	fetchSessionInfo,
	updateDefaultVersion,
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
	session.isLoggedIn && (await fetchSessionInfo())
	session.initialized = true
}

async function fetchSessionInfo() {
	if (!session.isLoggedIn) return
	const userInfo: SessionUser = await call('insights.api.get_user_info')
	Object.assign(session.user, {
		...userInfo,
		is_admin: Boolean(userInfo.is_admin),
		is_user: Boolean(userInfo.is_user),
		is_v2_instance: Boolean(userInfo.is_v2_instance),
	})
}

function updateDefaultVersion(version: SessionUser['default_version']) {
	session.user.default_version = version
	return call('insights.api.update_default_version', { version })
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
