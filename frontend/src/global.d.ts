declare module 'frappe-ui'

interface User {
	user_id: string
	first_name: string
	last_name: string
	full_name: string
	user_image: string
	is_admin: boolean
	is_user: boolean
}

interface AuthState {
	initialized: boolean
	user: User
}
