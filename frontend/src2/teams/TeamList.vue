<script setup lang="tsx">
import { Avatar, Breadcrumbs, ListView } from 'frappe-ui'
import { DatabaseIcon, PlusIcon, SearchIcon, Table2Icon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import UserSelector from '../components/UserSelector.vue'
import { copy } from '../helpers'
import session from '../session'
import useUserStore from '../users/users'
import TeamResourceSelector from './TeamResourceSelector.vue'
import useTeamStore, { Team, TeamPermission } from './teams'

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
const newTeamName = ref('')

const showEditTeamDialog = ref(false)
const editTeam = ref<Team | null>(null)
const teamModified = computed(() => {
	if (!editTeam.value) {
		return false
	}
	const team = teamStore.teams.find((t) => t.name === editTeam.value?.name)
	return JSON.stringify(team) !== JSON.stringify(editTeam.value)
})

const newMemberEmail = ref<string>('')
function addMember() {
	if (!editTeam.value || !newMemberEmail.value) {
		return
	}
	editTeam.value.team_members.push({
		user: newMemberEmail.value,
	})
	newMemberEmail.value = ''
}
function removeMember(userEmail: string) {
	if (!editTeam.value) {
		return
	}
	editTeam.value.team_members = editTeam.value.team_members.filter((u) => u.user !== userEmail)
}

const newResources = ref<TeamPermission[]>([])
function removePermission(perm: TeamPermission) {
	if (!editTeam.value) return
	editTeam.value.team_permissions = editTeam.value.team_permissions.filter(
		(p) => p.resource_name !== perm.resource_name
	)
}

document.title = 'Teams | Insights'
</script>

<template>
	<header class="mb-2 flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
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

	<div class="mb-4 flex h-full flex-col gap-2 overflow-auto px-4">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>
		<ListView class="h-full" v-bind="listOptions"> </ListView>
	</div>

	<Dialog
		v-model="showCreateTeamDialog"
		:options="{
			title: 'Create Team',
			actions: [
				{
					label: 'Create',
					variant: 'solid',
					disabled: !newTeamName || teamStore.creatingTeam,
					loading: teamStore.creatingTeam,
					onClick: () => {
						teamStore.createTeam(newTeamName).then(() => {
							showCreateTeamDialog = false
						})
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<FormControl label="Team Name" v-model="newTeamName" autocomplete="off" />
			</div>
		</template>
	</Dialog>

	<Dialog
		v-if="editTeam"
		v-model="showEditTeamDialog"
		:options="{
			title: 'Manage Team',
			actions: [
				{
					label: 'Done',
					variant: 'solid',
					disabled: !teamModified || teamStore.updatingTeam,
					loading: teamStore.updatingTeam,
					onClick: () => {
						if (!editTeam) return
						teamStore.updateTeam(editTeam).then(() => {
							showEditTeamDialog = false
						})
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="-mb-5 flex flex-col gap-4 text-base">
				<FormControl
					label="Team Name"
					v-model="editTeam.team_name"
					:disabled="editTeam.name === 'Admin'"
					autocomplete="off"
				/>

				<div class="flex flex-col gap-3">
					<div class="space-y-1.5">
						<label class="block text-xs text-gray-600">Members</label>
						<div class="flex w-full gap-2">
							<div class="flex-1">
								<UserSelector
									placeholder="Add members"
									v-model="newMemberEmail"
									:hide-users="editTeam.team_members.map((u) => u.user)"
								/>
							</div>
							<Button
								class="flex-shrink-0"
								variant="solid"
								label="Add"
								:disabled="!newMemberEmail"
								@click="addMember"
							></Button>
						</div>
					</div>

					<div class="flex max-h-[10rem] flex-col gap-1 overflow-y-auto">
						<div
							v-if="editTeam.team_members.length"
							v-for="member in editTeam.team_members"
							:key="member.user"
							class="flex w-full items-center gap-2 py-1"
						>
							<Avatar
								size="xl"
								:label="userStore.getUser(member.user)?.full_name"
								:image="userStore.getUser(member.user)?.user_image"
							/>
							<div class="flex flex-1 flex-col">
								<div class="leading-5">
									{{ userStore.getUser(member.user)?.full_name }}
								</div>
								<div class="text-xs text-gray-600">
									{{ userStore.getUser(member.user)?.email }}
								</div>
							</div>
							<Button
								variant="ghost"
								icon="x"
								class="flex-shrink-0"
								@click="removeMember(member.user)"
							/>
						</div>
						<div
							v-else
							class="rounded border border-dashed border-gray-300 px-32 py-6 text-center text-sm text-gray-500"
						>
							This team does not have any members
						</div>
					</div>
				</div>

				<div class="flex flex-col gap-3">
					<div class="space-y-1.5">
						<label class="block text-xs text-gray-600">Access</label>
						<p
							v-if="editTeam.name == 'Admin'"
							class="rounded bg-gray-50 p-2 text-sm leading-4 text-gray-600"
						>
							Admin team has access to all the data sources and tables. Members of
							this team are allowed to manage teams, users, and other admin settings
						</p>
						<div v-else class="flex w-full gap-2">
							<div class="flex-1">
								<TeamResourceSelector v-model="newResources" :team="editTeam" />
							</div>
						</div>
					</div>

					<div
						v-if="editTeam.name !== 'Admin'"
						class="flex max-h-[10rem] flex-col divide-y overflow-y-auto"
					>
						<div
							v-if="editTeam.team_permissions.length"
							v-for="perm in editTeam.team_permissions"
							:key="`${perm.resource_type}-${perm.resource_name}`"
							class="flex w-full items-center gap-2 py-1"
						>
							<DatabaseIcon
								v-if="perm.resource_type_label == 'Source'"
								class="h-4 w-4 text-gray-700"
								stroke-width="1.5"
							/>
							<Table2Icon
								v-else-if="perm.resource_type_label == 'Table'"
								class="h-4 w-4 text-gray-700"
								stroke-width="1.5"
							/>
							<div class="flex flex-1 items-baseline gap-2">
								<div class="">{{ perm.label }}</div>
								<div class="text-xs text-gray-600">{{ perm.description }}</div>
							</div>
							<Badge size="md">{{ perm.resource_type_label }}</Badge>
							<Button
								variant="ghost"
								icon="x"
								class="flex-shrink-0"
								@click="removePermission(perm)"
							/>
						</div>
						<div
							v-else
							class="rounded border border-dashed border-gray-300 px-32 py-6 text-center text-sm text-gray-500"
						>
							This team does not have access to any data sources or tables
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
