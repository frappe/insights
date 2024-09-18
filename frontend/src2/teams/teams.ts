import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import { createToast } from '../helpers/toasts'
import { User } from '../users/users'

export type Team = {
	name: string
	team_name: string
	owner: string
	creation: string
	creation_from_now: string
	team_members: User[]
}
const teams = ref<Team[]>([])

const loading = ref(false)
async function getTeams(search_term = '') {
	loading.value = true
	return call('insights.api.user.get_teams', { search_term }).then((res: Team[]) => {
		teams.value = res.map((t: any) => {
			return {
				...t,
				creation_from_now: useTimeAgo(t.creation),
			}
		})
		loading.value = false
		return teams.value
	})
}

const creatingTeam = ref(false)
async function createTeam(team_name: string) {
	creatingTeam.value = true
	return call('insights.api.user.create_team', { team_name })
		.then(() => {
			getTeams()
			createToast({
				message: 'Team created',
				variant: 'success',
			})
		})
		.catch((e: Error) => {
			showErrorToast(e)
		})
		.finally(() => {
			creatingTeam.value = false
		})
}

const updatingTeam = ref(false)
async function updateTeam(team: Team) {
	updatingTeam.value = true
	return call('insights.api.user.update_team', { team })
		.then(() => {
			getTeams()
			createToast({
				message: 'Team updated',
				variant: 'success',
			})
		})
		.catch((e: Error) => {
			showErrorToast(e)
		})
		.finally(() => {
			updatingTeam.value = false
		})
}

export default function useTeamStore() {
	if (!teams.value.length) {
		getTeams()
	}

	return reactive({
		teams,
		loading,
		getTeams,

		creatingTeam,
		createTeam,

		updatingTeam,
		updateTeam,
	})
}
