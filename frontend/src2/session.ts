import { call } from 'frappe-ui'
import { computed, reactive } from 'vue'

const emptyUser: User = {
	email: '',
	first_name: '',
	last_name: '',
	full_name: '',
	user_image: '',
	is_admin: false,
	is_user: false,
	country: '',
	locale: 'en-US',
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

async function initialize(force: boolean = false) {
	if (session.initialized && !force) return
	Object.assign(session.user, getSessionFromCookies())
	session.isLoggedIn && (await fetchSessionInfo())
	session.isLoggedIn && call('insights.api.telemetry.track_active_site')
	session.initialized = true
}

async function fetchSessionInfo() {
	if (!session.isLoggedIn) return
	const userInfo: User = await call('insights.api.get_user_info')
	Object.assign(session.user, {
		...userInfo,
		is_admin: Boolean(userInfo.is_admin),
		is_user: Boolean(userInfo.is_user),
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
