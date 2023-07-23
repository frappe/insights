import { call, createResource } from 'frappe-ui'
import { reactive, watch } from 'vue'
import subscription from '@/subscription'

const auth = reactive({
	isLoggedIn: false,
	user: {
		user_id: '',
		first_name: '',
		last_name: '',
		full_name: '',
		user_image: '',
		is_admin: undefined,
		is_user: undefined,
	},
	login,
	logout,
	reset,
	isAuthorized,
	createViewLog,
})

// fetch inital state from cookies
document.cookie
	.split('; ')
	.map((c) => c.split('='))
	.forEach(([key, value]) => {
		auth.user[key] = decodeURIComponent(value)
		if (key === 'user_id') {
			auth.isLoggedIn = value !== 'Guest'
			trackActiveSite()
		}
	})

const userInfo = createResource({
	url: 'insights.api.get_user_info',
	onSuccess(res) {
		auth.user.is_admin = res.is_admin
		auth.user.is_user = res.is_user
		auth.user.first_name = res.first_name
		auth.user.last_name = res.last_name
	},
})

watch(
	() => auth.isLoggedIn,
	(newVal, oldVal) => {
		if (newVal && !oldVal) {
			userInfo.fetch()
			subscription.fetchTrialStatus()
			trackActiveSite()
		}
	}
)

async function login(email, password) {
	reset()
	let res = await call('login', {
		usr: email,
		pwd: password,
	})
	if (res) {
		auth.user.first_name = res.first_name
		auth.user.last_name = res.last_name
		auth.user.full_name = res.full_name
		auth.user.user_image = res.user_image
		auth.isLoggedIn = true
		window.location.reload()
	}
	return auth.isLoggedIn
}

async function logout() {
	reset()
	await call('logout')
	window.location.reload()
}

function reset() {
	auth.isLoggedIn = false
	auth.user = {
		user_id: '',
		full_name: '',
		user_image: '',
		is_admin: undefined,
		is_user: undefined,
	}
}

async function isAuthorized() {
	if (auth.user.is_admin === undefined) {
		await userInfo.fetch()
	}
	return auth.user.is_admin || auth.user.is_user
}

async function createViewLog(recordType, recordName) {
	if (!auth.isLoggedIn) return
	await call('insights.api.home.create_last_viewed_log', {
		record_type: recordType,
		record_name: recordName,
	})
}

async function trackActiveSite() {
	auth.isLoggedIn && call('insights.api.telemetry.track_active_site')
}

export default auth
