import { reactive, computed } from 'vue'
import { createResource } from 'frappe-ui'

const userListResource = createResource('insights.api.user.get_users')
const addUserResource = createResource({
	url: 'insights.api.user.add_insights_user',
})

export function useUsers() {
	const users = reactive({
		list: computed(() => userListResource.data),
		loading: computed(() => userListResource.loading),
		error: computed(() => userListResource.error),
		refresh: () => userListResource.fetch(),
		add: (user) => addUserResource.submit({ user }).then(() => userListResource.fetch()),
	})

	return users
}
