import { reactive, computed } from 'vue'
import { createDocumentResource, createResource, debounce } from 'frappe-ui'
import { showPrompt } from './prompt'
import { useUsers } from './useUsers'

const users = useUsers()
const teamListResource = createResource(
	'insights.insights.doctype.insights_team.insights_team_client.get_teams'
)

export function useTeams() {
	const teams = reactive({
		list: computed(() => teamListResource.data),
		loading: computed(() => teamListResource.loading),
		error: computed(() => teamListResource.error),
		refresh: () => teamListResource.fetch(),
	})

	return teams
}

export function useTeam(teamname) {
	const team = createDocumentResource({
		doctype: 'Insights Team',
		name: teamname,
		whitelistedMethods: {
			get_members_and_resources: 'get_members_and_resources',
			search_team_members: 'search_team_members',
			search_team_resources: 'search_team_resources',
			add_team_member: 'add_team_member',
			add_team_members: 'add_team_members',
			remove_team_member: 'remove_team_member',
			add_team_resource: 'add_team_resource',
			add_team_resources: 'add_team_resources',
			remove_team_resource: 'remove_team_resource',
			delete_team: 'delete_team',
		},
	})
	team.get_members_and_resources.fetch()
	team.members = computed(() => team.get_members_and_resources.data?.members)
	team.resources = computed(() => team.get_members_and_resources.data?.resources)

	team.searchMembers = debounce((query) => {
		if (!query && query !== '') {
			team.memberOptions = []
			return
		}
		return team.search_team_members.submit({ query }).then((data) => {
			team.memberOptions = data || []
		})
	}, 500)
	team.searchMembers('')

	team.addMember = (member) => {
		return team.add_team_member
			.submit({ user: member })
			.then(team.get_members_and_resources.fetch)
			.then(users.refresh)
	}
	team.addMembers = (members) => {
		return team.add_team_members
			.submit({ users: members })
			.then(team.get_members_and_resources.fetch)
			.then(users.refresh)
	}

	team.removeMember = (member) => {
		showPrompt({
			title: 'Remove Member',
			message: `Are you sure you want to remove ${member} from this team?`,
			icon: { name: 'trash', variant: 'danger' },
			primaryAction: {
				label: 'Remove',
				variant: 'danger',
				action: ({ close }) => {
					return team.remove_team_member
						.submit({ user: member })
						.then(team.get_members_and_resources.fetch)
						.then(users.refresh)
						.then(close)
				},
			},
		})
	}

	team.searchResources = debounce((resource_type, query) => {
		if (!query && query !== '') {
			team.resourceOptions = []
			return
		}
		return team.search_team_resources.submit({ resource_type, query }).then((data) => {
			team.resourceOptions = data || []
		})
	}, 500)

	team.addResource = (resource) => {
		return team.add_team_resource
			.submit({ resource })
			.then(team.get_members_and_resources.fetch)
	}
	team.addResources = (resources) => {
		return team.add_team_resources
			.submit({ resources })
			.then(team.get_members_and_resources.fetch)
	}

	team.removeResource = (resource) => {
		return team.remove_team_resource
			.submit({ resource })
			.then(team.get_members_and_resources.fetch)
	}

	team.deleteTeam = () => {
		return team.delete_team.submit().then(teamListResource.fetch).then(users.refresh)
	}

	return team
}
