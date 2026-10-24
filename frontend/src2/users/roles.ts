import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'

const roles = ref<string[]>([])
const loading = ref(false)

function getRoles() {
	loading.value = true
	return call('insights.api.user.get_roles')
		.then((res: unknown) => {
			roles.value = res as string[]
			return roles.value
		})
		.catch(showErrorToast)
		.finally(() => (loading.value = false))
}

export default function useRoleStore() {
	if (!roles.value.length && !loading.value) {
		getRoles()
	}

	return reactive({
		roles,
		loading,
		getRoles,
	})
}
