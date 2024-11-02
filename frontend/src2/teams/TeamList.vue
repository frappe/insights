<script setup lang="tsx">
import { Avatar, Breadcrumbs, ListView } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { copy } from '../helpers'
import session from '../session'
import useUserStore from '../users/users'
import ManageTeamDialog from './ManageTeamDialog.vue'
import useTeamStore, { Team } from './teams'
import CreateTeamDialog from './CreateTeamDialog.vue'

const userStore = useUserStore()
const teamStore = useTeamStore()
teamStore.getTeams()

const searchQuery = ref('')
const filteredTeams = computed(() => {
	if (!searchQuery.value) {
		return teamStore.teams
	}
	return teamStore.teams.filter((team) =>
		team.team_name.toLowerCase().includes(searchQuery.value.toLowerCase())
	)
})

const listOptions = ref({
	columns: [
		{
			label: 'Team',
			key: 'team_name',
		},
		{
			label: 'Owner',
			key: 'owner',
			getLabel(props: any) {
				const team = props.row as Team
				const user = userStore.getUser(team.owner)
				return user?.full_name || team.owner
			},
			prefix(props: any) {
				const team = props.row as Team
				const imageUrl = userStore.getUser(team.owner)?.user_image
				return <Avatar size="md" label={team.owner} image={imageUrl} />
			},
		},
		{
			label: 'Creation',
			key: 'creation_from_now',
		},
	],
	rows: filteredTeams,
	rowKey: 'team_name',
	options: {
		showTooltip: false,
		onRowClick: (team: Team) => {
			editTeam.value = copy(team)
			showEditTeamDialog.value = true
		},
		emptyState: {
			title: 'No teams.',
			description: 'No teams to display.',
			button: session.user.is_admin
				? {
						label: 'Create Team',
						variant: 'solid',
						onClick: () => (showCreateTeamDialog.value = true),
				  }
				: undefined,
		},
	},
})

const showCreateTeamDialog = ref(false)
const showEditTeamDialog = ref(false)
const editTeam = ref<Team | null>(null)

document.title = 'Teams | Insights'
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: 'Teams', route: '/teams' }]" />
		<div class="flex items-center gap-2">
			<Button
				v-if="session.user.is_admin"
				label="Create Team"
				variant="solid"
				@click="showCreateTeamDialog = true"
			>
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>
		<ListView class="h-full" v-bind="listOptions"> </ListView>
	</div>
	<CreateTeamDialog v-model="showCreateTeamDialog" />
	<ManageTeamDialog
		v-if="editTeam"
		:key="editTeam.name"
		v-model="showEditTeamDialog"
		:team="editTeam"
	/>
</template>
