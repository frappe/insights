import { call, createResource } from 'frappe-ui'
import { reactive, watch } from 'vue'

const auth = reactive({
	isLoggedIn: false,
	user: {
		user_id: '',
		full_name: '',
		user_image: '',
		permissions: undefined,
	},
	login,
	logout,
	reset,
	hasPermission,
})

// fetch inital state from cookies
document.cookie
	.split('; ')
	.map((c) => c.split('='))
	.forEach(([key, value]) => {
		auth.user[key] = decodeURIComponent(value)
		if (key === 'user_id') {
			auth.isLoggedIn = value !== 'Guest'
		}
	})

const userInfo = createResource({
	method: 'insights.api.get_user_info',
	onSuccess(res) {
		auth.user.permissions = res.permissions
	},
})

watch(
	() => auth.isLoggedIn,
	(newVal, oldVal) => {
		if (newVal && !oldVal) {
			userInfo.fetch()
		}
	},
	{ immediate: true }
)

async function login(email, password) {
	reset()
	let res = await call('login', {
		usr: email,
		pwd: password,
	})
	if (res) {
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
		permissions: undefined,
	}
}

async function hasPermission(permission) {
	if (!auth.user.permissions) {
		await userInfo.fetch()
	}
	return auth.user.permissions[permission]
}

export default auth
