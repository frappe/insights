<script setup lang="ts">
import { computed, ref } from 'vue'
import useTeamStore, { Team, TeamPermission } from './teams'
import useUserStore from '../users/users'
import { Database, Table2 } from 'lucide-vue-next'
import TeamResourceSelector from './TeamResourceSelector.vue'
import UserSelector from '../components/UserSelector.vue'

const props = defineProps<{ team: Team }>()
const show = defineModel()

const teamStore = useTeamStore()
const userStore = useUserStore()

const teamModified = computed(() => {
	if (!props.team) {
		return false
	}
	const team = teamStore.teams.find((t) => t.name === props.team?.name)
	return JSON.stringify(team) !== JSON.stringify(props.team)
})

const newMemberEmail = ref<string>('')
function addMember() {
	if (!props.team || !newMemberEmail.value) {
		return
	}
	props.team.team_members.push({
		user: newMemberEmail.value,
	})
	newMemberEmail.value = ''
}
function removeMember(userEmail: string) {
	if (!props.team) {
		return
	}
	props.team.team_members = props.team.team_members.filter((u) => u.user !== userEmail)
}

const newResources = ref<TeamPermission[]>([])
function removePermission(perm: TeamPermission) {
	if (!props.team) return
	props.team.team_permissions = props.team.team_permissions.filter(
		(p) => p.resource_name !== perm.resource_name
	)
}
</script>

<template>
	<Dialog
		v-if="props.team"
		v-model="show"
		:options="{
			title: 'Manage Team',
			actions: [
				{
					label: 'Done',
					variant: 'solid',
					disabled: !teamModified || teamStore.updatingTeam,
					loading: teamStore.updatingTeam,
					onClick: () => {
						if (!props.team) return
						teamStore.updateTeam(props.team).then(() => {
							show = false
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
					v-model="props.team.team_name"
					:disabled="props.team.name === 'Admin'"
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
									:hide-users="props.team.team_members.map((u) => u.user)"
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
							v-if="props.team.team_members.length"
							v-for="member in props.team.team_members"
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
							v-if="props.team.name == 'Admin'"
							class="rounded bg-gray-50 p-2 text-sm leading-4 text-gray-600"
						>
							Admin team has access to all the data sources and tables. Members of
							this team are allowed to manage teams, users, and other admin settings
						</p>
						<div v-else class="flex w-full gap-2">
							<div class="flex-1">
								<TeamResourceSelector v-model="newResources" :team="props.team" />
							</div>
						</div>
					</div>

					<div
						v-if="props.team.name !== 'Admin'"
						class="flex max-h-[10rem] flex-col divide-y overflow-y-auto"
					>
						<div
							v-if="props.team.team_permissions.length"
							v-for="perm in props.team.team_permissions"
							:key="`${perm.resource_type}-${perm.resource_name}`"
							class="flex w-full items-center gap-2 py-1"
						>
							<Database
								v-if="perm.resource_type_label == 'Source'"
								class="h-4 w-4 text-gray-700"
								stroke-width="1.5"
							/>
							<Table2
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
