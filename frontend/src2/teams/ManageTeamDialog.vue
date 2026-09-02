<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import UserSelector from '../components/UserSelector.vue'
import { copy } from '../helpers'
import session from '../session'
import { __ } from '../translation'
import useUserStore from '../users/users'
import TeamResourceSelector from './TeamResourceSelector.vue'
import useTeamStore, { Team } from './teams'

const props = defineProps<{ team: Team }>()
const show = defineModel()

const currentTeam = ref(copy(props.team))
const teamStore = useTeamStore()
const userStore = useUserStore()

watch(
	() => show.value,
	(isOpen) => {
		if (isOpen) {
			userStore.getUsers()
		}
	},
	{ immediate: true },
)

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
		(u) => u.user !== userEmail,
	)
}

const activeTab = ref('Members')
</script>

<template>
	<Dialog
		v-if="currentTeam"
		v-model:open="show"
		:title="__('Manage Team')"
		:actions="
			[
				{
					label: __('Done'),
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
				session.user.is_admin && currentTeam.name !== 'Admin'
					? {
							label: __('Delete'),
							variant: 'subtle',
							theme: 'red',
							loading: teamStore.deletingTeam,
							onClick: () =>
								teamStore.deleteTeam(currentTeam.name).then(() => (show = false)),
					  }
					: null,
			].filter(Boolean)
		"
	>
		<template #default>
			<div class="-mb-5 flex h-[25rem] flex-col gap-4 text-base">
				<FormControl
					label="Team Name"
					v-model="currentTeam.team_name"
					:disabled="currentTeam.name === 'Admin'"
					autocomplete="off"
					class="flex-shrink-0"
				/>

				<TabButtons
					:options="[
						{ label: __('Members'), value: 'Members' },
						{ label: __('Access'), value: 'Access' },
					]"
					v-model="activeTab"
					class="full-tabs flex-shrink-0"
				/>

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
						<div v-if="userStore.loading" class="flex items-center justify-center py-8">
							<LoadingIndicator class="h-6 w-6 text-ink-gray-5" />
						</div>
						<div
							v-else-if="currentTeam.team_members.length"
							v-for="member in currentTeam.team_members"
							:key="member.user"
							class="flex w-full items-center gap-2 py-1"
						>
							<Avatar
								size="xl"
								:label="userStore.getUser(member.user)?.full_name || member.user"
								:image="userStore.getUser(member.user)?.user_image"
							/>
							<div class="flex flex-1 flex-col">
								<div class="leading-5">
									{{ userStore.getUser(member.user)?.full_name || member.user }}
								</div>
								<div class="text-xs text-ink-gray-5">
									{{ userStore.getUser(member.user)?.email || member.user }}
								</div>
							</div>
							<Button
								variant="ghost"
								icon="lucide-x"
								class="flex-shrink-0"
								@click="removeMember(member.user)"
							/>
						</div>
						<div
							v-else
							class="rounded-4 border border-dashed border-outline-gray-2 px-32 py-6 text-center text-sm text-ink-gray-4"
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
						class="rounded-4 bg-surface-gray-1 p-2 text-p-sm text-ink-gray-5"
					>
						Admin team has access to all the data sources and tables. Members of this
						team are allowed to manage teams, users, and other admin settings
					</div>

					<Suspense v-else>
						<TeamResourceSelector v-model="currentTeam.team_permissions" />
						<template #fallback>
							<div class="flex h-32 items-center justify-center">
								<LoadingIndicator class="h-6 w-6 text-ink-gray-5" />
							</div>
						</template>
					</Suspense>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<style scoped>
/* Stretch the standard TabButtons into a full-width, equal-halves segmented bar
   (its inner flex container is content-width by default, not reachable via props). */
.full-tabs :deep(div) {
	width: 100%;
}
.full-tabs :deep([data-slot='tab-button']) {
	flex: 1 1 0%;
}
.full-tabs :deep([data-slot='tab-button'] > *) {
	width: 100%;
}
</style>
