import { useTimeAgo } from '@vueuse/core'
import { __ } from '../translation'
import { call, toast } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'

export type TeamMember = {
	user: string
}
export type TeamPermission = {
	type: 'Source' | 'Table'
	resource_type: 'Insights Data Source v3' | 'Insights Table v3'
	resource_name: string
	table_restrictions?: string
}
export type Team = {
	name: string
	team_name: string
	owner: string
	creation: string
	creation_from_now: string
	team_members: TeamMember[]
	team_permissions: TeamPermission[]
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
				team_permissions: t.team_permissions.map((p: any) => {
					return {
						...p,
						type: getResourceTypeLabel(p.resource_type),
					}
				}),
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
			toast.success(__('Team created'))
		})
		.catch((e: Error) => {
			showErrorToast(e)
		})
		.finally(() => {
			creatingTeam.value = false
		})
}

const deletingTeam = ref(false)
function deleteTeam(team_name: string) {
	return new Promise<void>((resolve, reject) => {
		confirmDialog({
			title: __('Delete Team'),
			message: __('Are you sure you want to delete this team?'),
			onSuccess: () => {
				deletingTeam.value = true
				call('insights.api.user.delete_team', { team_name })
					.then(() => {
						getTeams()
						toast.success(__('Team deleted'))
						resolve()
					})
					.catch((e: Error) => {
						showErrorToast(e)
						reject(e)
					})
					.finally(() => {
						deletingTeam.value = false
					})
			},
		})
	})
}

const updatingTeam = ref(false)
async function updateTeam(team: Team) {
	updatingTeam.value = true
	return call('insights.api.user.update_team', { team })
		.then(() => {
			getTeams()
			toast.success(__('Team updated'))
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

		deletingTeam,
		deleteTeam,
	})
}

function getResourceTypeLabel(resource_type: string) {
	if (resource_type === 'Insights Data Source v3') {
		return 'Source'
	}
	if (resource_type === 'Insights Table v3') {
		return 'Table'
	}
}
