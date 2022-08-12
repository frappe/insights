import { call } from 'frappe-ui'
import settings from '@/utils/settings'
import { reactive, ref, watch } from 'vue'

const auth = reactive({
	isLoggedIn: ref(localStorage.getItem('isLoggedIn') !== null),
	user: {
		user_id: '',
		full_name: '',
		user_image: '',
	},
	login,
	logout,
	reset,
})

document.cookie
	.split('; ')
	.map((c) => c.split('='))
	.forEach(([key, value]) => {
		auth.user[key] = decodeURIComponent(value)
		if (key === 'user_id') {
			auth.isLoggedIn = value !== 'Guest'
			localStorage.setItem('isLoggedIn', value !== 'Guest')
		}
	})

watch(
	() => auth.isLoggedIn,
	(newVal, oldVal) => {
		if (newVal && !oldVal) {
			settings.fetch()
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
		localStorage.setItem('isLoggedIn', true)
		auth.user.full_name = res.full_name
		auth.user.user_image = res.user_image
		auth.isLoggedIn = true
	}
	return auth.isLoggedIn
}
async function logout() {
	reset()
	await call('logout')
	window.location.reload()
}
function reset() {
	localStorage.removeItem('isLoggedIn')
	auth.isLoggedIn = false
}

export default auth
