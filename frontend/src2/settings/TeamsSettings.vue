<script setup lang="tsx">
import { Avatar, ListView } from 'frappe-ui'
import { Plus, SearchIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { copy } from '../helpers'
import session from '../session'
import CreateTeamDialog from '../teams/CreateTeamDialog.vue'
import useTeamStore, { Team } from '../teams/teams'

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
			prefix(props: any) {
				const team = props.row as Team
				return <Avatar size="md" label={team.team_name} />
			},
		},
	],
	rows: filteredTeams,
	rowKey: 'team_name',
	options: {
		selectable: false,
		showTooltip: false,
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
</script>

<template>
	<div class="flex h-full w-full flex-col gap-3 overflow-x-hidden overflow-y-scroll p-8 px-10">
		<h1 class="flex-shrink-0 text-xl font-semibold">Teams</h1>
		<div class="flex w-full flex-1 flex-col gap-3 overflow-auto">
			<div class="flex justify-between gap-2 overflow-visible py-1">
				<FormControl placeholder="Search" v-model="searchQuery" :debounce="300">
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-gray-500" stroke-width="1.5" />
					</template>
				</FormControl>

				<Button
					v-if="session.user.is_admin"
					label="Create Team"
					variant="outline"
					@click="showCreateTeamDialog = true"
				>
					<template #prefix>
						<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</div>
			<ListView class="h-full" v-bind="listOptions"> </ListView>
		</div>
		<CreateTeamDialog v-model="showCreateTeamDialog" />
	</div>
</template>
