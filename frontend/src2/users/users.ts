import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { createToast } from '../helpers/toasts'
import { showErrorToast } from '../helpers'
import { __ } from '../translation'

export type User = {
	name: ''
	email: ''
	full_name: ''
	user_image: ''
	type: 'Admin' | 'User'
	enabled: 1 | 0
	last_active?: ''
	invitation_status?: 'Pending' | 'Expired'
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

function getUser(email: string) {
	return users.value.find((user) => user.email === email)
}
function getName(email: string) {
	const user = getUser(email)
	return user ? user.full_name || email : ''
}
function getImage(email: string) {
	const user = getUser(email)
	return user ? user.user_image : ''
}

const sendingInvitation = ref(false)
function inviteUsers(emails: string[]) {
	sendingInvitation.value = true
	return call('insights.api.user.invite_users', { emails: emails.join(',') })
		.then(() => {
			getUsers()
			createToast({
				title: __('Invitation Sent'),
				message:
					emails.length === 1
						? __(`Invitation sent to {0}`, emails[0])
						: __(`Invitations sent to {0} users`, String(emails.length)),
				variant: 'success',
			})
		})
		.catch((e: Error) => {
			showErrorToast(e)
		})
		.finally(() => {
			sendingInvitation.value = false
		})
}

const updatingUser = ref(false)
type UpdateUser = {
	first_name: string
	last_name: string
}
function updateUser(email: string, data: Partial<UpdateUser>) {
	updatingUser.value = true
	return call('insights.api.user.update_user', {
		email,
		fields: {
			first_name: data.first_name,
			last_name: data.last_name,
		},
	})
		.then(() => {
			getUsers()
			createToast({
				title: __('User Updated'),
				message: __('User updated successfully'),
				variant: 'success',
			})
		})
		.catch((e: Error) => {
			showErrorToast(e)
		})
		.finally(() => {
			updatingUser.value = false
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
		getUser,
		getName,
		getImage,

		updatingUser,
		updateUser,

		inviteUsers,
		sendingInvitation,
	})
}
