<script setup lang="ts">
import { computed, ref } from 'vue'
import Switch from '../components/Switch.vue'
import UserSelector from '../components/UserSelector.vue'
import { copy } from '../helpers'
import useUserStore from '../users/users'
import TeamResourceSelector from './TeamResourceSelector.vue'
import useTeamStore, { Team } from './teams'

const props = defineProps<{ team: Team }>()
const show = defineModel()

const currentTeam = ref(copy(props.team))
const teamStore = useTeamStore()
const userStore = useUserStore()

const teamModified = computed(() => {
	if (!currentTeam.value) {
		return false
	}
	const team = teamStore.teams.find((t) => t.name === currentTeam.value.name)
	return JSON.stringify(team) !== JSON.stringify(currentTeam.value)
})

const newMemberEmail = ref<string>('')
function addMember() {
	if (!currentTeam.value || !newMemberEmail.value) {
		return
	}
	currentTeam.value.team_members.push({
		user: newMemberEmail.value,
	})
	newMemberEmail.value = ''
}
function removeMember(userEmail: string) {
	if (!currentTeam.value) {
		return
	}
	currentTeam.value.team_members = currentTeam.value.team_members.filter(
		(u) => u.user !== userEmail
	)
}

const activeTab = ref('Members')
</script>

<template>
	<Dialog
		v-if="currentTeam"
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
						if (!currentTeam) return
						teamStore.updateTeam(currentTeam).then(() => {
							show = false
						})
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="-mb-5 flex h-[25rem] flex-col gap-4 text-base">
				<FormControl
					label="Team Name"
					v-model="currentTeam.team_name"
					:disabled="currentTeam.name === 'Admin'"
					autocomplete="off"
					class="flex-shrink-0"
				/>

				<Switch
					:tabs="['Members', 'Access']"
					v-model="activeTab"
					class="flex-shrink-0"
				></Switch>

				<!-- Manage Members -->
				<div
					v-show="activeTab == 'Members'"
					class="flex flex-1 flex-col gap-3 overflow-hidden"
				>
					<div class="flex w-full flex-shrink-0 gap-2">
						<div class="flex-1">
							<UserSelector
								placeholder="Add members"
								v-model="newMemberEmail"
								:hide-users="currentTeam.team_members.map((u) => u.user)"
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

					<div class="flex flex-1 flex-col gap-1 overflow-y-auto">
						<div
							v-if="currentTeam.team_members.length"
							v-for="member in currentTeam.team_members"
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

				<!-- Manage Access -->
				<div
					v-show="activeTab == 'Access'"
					class="relative flex flex-1 flex-col gap-1 overflow-y-auto"
				>
					<div
						v-if="currentTeam.name == 'Admin'"
						class="rounded bg-gray-50 p-2 text-p-sm text-gray-600"
					>
						Admin team has access to all the data sources and tables. Members of this
						team are allowed to manage teams, users, and other admin settings
					</div>

					<Suspense v-else>
						<TeamResourceSelector v-model="currentTeam.team_permissions" />
						<template #fallback>
							<div class="flex h-32 items-center justify-center">
								<LoadingIndicator class="h-6 w-6 text-gray-600" />
							</div>
						</template>
					</Suspense>
				</div>
			</div>
		</template>
	</Dialog>
</template>
