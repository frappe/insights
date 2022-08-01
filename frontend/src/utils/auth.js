import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'

export const isLoggedIn = ref(localStorage.getItem('isLoggedIn') !== null)
export const user = reactive({
	full_name: '',
	user_image: '',
})

let cookies = document.cookie.split('; ')
cookies
	.map((c) => c.split('='))
	.forEach(([key, value]) => {
		user[key] = value
	})

export async function login(email, password) {
	localStorage.removeItem('isLoggedIn')
	isLoggedIn.value = false
	let res = await call('login', {
		usr: email,
		pwd: password,
	})
	if (res) {
		console.log(res)
		localStorage.setItem('isLoggedIn', true)
		user.full_name = res.full_name
		user.user_image = res.user_image
		isLoggedIn.value = true
	}
	return isLoggedIn.value
}
export async function logout() {
	localStorage.removeItem('isLoggedIn')
	isLoggedIn.value = false
	await call('logout')
	window.location.reload()
}
