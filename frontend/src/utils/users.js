import { createResource } from 'frappe-ui'

export let usersResource = createResource({
	method: 'analytics.api.user.get_user_info',
	cache: 'users',
	initialData: {},
})
usersResource.fetch()

export function userInfo(email) {
	if (!email) {
		email = sessionUser()
	}
	let fallback = {
		name: email,
		email: email,
		full_name: email.split('@')[0],
		user_image: null,
	}
	return usersResource.data[email] || fallback
}

let _sessionUser = null
export function sessionUser() {
	if (!_sessionUser) {
		let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
		_sessionUser = cookies.get('user_id')
	}
	return _sessionUser
}
