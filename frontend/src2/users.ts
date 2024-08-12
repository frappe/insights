import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'

type User = {
	email: ''
	first_name: ''
	last_name: ''
	full_name: ''
	user_image: ''
}
const users = ref<User[]>([])

const loading = ref(false)
async function getUsers(search_term = '') {
	loading.value = true
	return call('insights.api.user.get_users', { search_term }).then((res: User[]) => {
		users.value = res
		loading.value = false
		return users.value
	})
}

export default function useUserStore() {
	if (!users.value.length) {
		getUsers()
	}

	return reactive({
		users,
		loading,
		getUsers,
		getUser(email: string) {
			return users.value.find((user) => user.email === email)
		}
	})
}
