<script setup lang="ts">
import { Badge, Tooltip } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import UserSelector from '../components/UserSelector.vue'
import VisibilitySelector from '../components/VisibilitySelector.vue'
import { copy, copyToClipboard } from '../helpers'
import session from '../session'
import { Visibility } from '../types/workbook.types'
import useUserStore from '../users/users'
import { Dashboard } from './dashboard'
import { createToast } from '../helpers/toasts'
import { __ } from '../translation'

const show = defineModel()

const dashboard = inject('dashboard') as Dashboard

const visibility = ref<Visibility>(declaredVisibility())
const visibleToRoles = ref((dashboard.doc.visible_to_roles || []).map((r) => r.role))
const peopleWithAccess = ref(copy(dashboard.doc.people_with_access))

function declaredVisibility(): Visibility {
	const declared = dashboard.doc.visibility
	if (declared && declared !== 'Private') return declared
	// dashboards shared with the organization before the ladder existed
	if (dashboard.doc.is_shared_with_organization) return 'Everyone'
	return 'Private'
}

const shareLink = computed(() => dashboard.getShareLink())
const iFrameLink = computed(() => {
	return `<iframe src="${shareLink.value}" width="100%" height="100%" frameborder="0"></iframe>`
})

const hasChanged = computed(() => {
	const prev = {
		visibility: visibility.value,
		visible_to_roles: visibleToRoles.value,
		people_with_access: peopleWithAccess.value.map((u) => u.email),
	}
	const next = {
		visibility: declaredVisibility(),
		visible_to_roles: (dashboard.doc.visible_to_roles || []).map((r) => r.role),
		people_with_access: dashboard.doc.people_with_access.map((u) => u.email),
	}
	return JSON.stringify(prev) !== JSON.stringify(next)
})

async function saveChanges() {
	dashboard.doc.visibility = visibility.value
	dashboard.doc.visible_to_roles = visibleToRoles.value.map((role) => ({ role }))
	await dashboard.save()
	await dashboard.updateAccess({
		// the ladder owns the audience; the org DocShare mirrors its `Everyone`
		// rung, because a share is what dashboards had before the ladder and what
		// `declaredVisibility` above still reads for them
		is_shared_with_organization: visibility.value === 'Everyone',
		people_with_access: peopleWithAccess.value.map((u) => u.email),
	})
	createToast({
		variant: 'success',
		title: __('Dashboard Access Updated'),
	})
	show.value = false
}

const selectedUserEmail = ref<string>('')
const userStore = useUserStore()
function addSharedUser() {
	if (!selectedUserEmail.value) return
	if (!peopleWithAccess.value) peopleWithAccess.value = []
	peopleWithAccess.value.push({
		email: selectedUserEmail.value,
		full_name: userStore.getName(selectedUserEmail.value),
		user_image: userStore.getImage(selectedUserEmail.value),
	})
	selectedUserEmail.value = ''
}
</script>

<template>
	<Dialog
		v-model:open="show"
		:title="__('Share Dashboard')"
		:actions="[
			{
				label: __('Done'),
				variant: 'solid',
				disabled: !hasChanged,
				onClick: saveChanges,
			},
		]"
	>
		<template #default>
			<div class="flex flex-col gap-4">
				<VisibilitySelector v-model:visibility="visibility" v-model:roles="visibleToRoles">
					<template #actions>
						<Tooltip text="Copy Link" :hoverDelay="0.1">
							<Button icon="lucide-link-2" @click="copyToClipboard(shareLink)">
							</Button>
						</Tooltip>
						<Tooltip text="Copy Embed" :hoverDelay="0.1">
							<Button icon="lucide-code" @click="copyToClipboard(iFrameLink)">
							</Button>
						</Tooltip>
					</template>
				</VisibilitySelector>

				<hr class="my-1 border-t border-outline-gray-1" />

				<div class="flex flex-col">
					<div class="mb-4 flex w-full gap-2">
						<div class="flex-1">
							<UserSelector
								v-model="selectedUserEmail"
								placeholder="Search by name or email"
								:hide-users="peopleWithAccess.map((u) => u.email)"
							/>
						</div>
						<Button
							class="flex-shrink-0"
							variant="solid"
							label="Share"
							:disabled="!selectedUserEmail"
							@click="addSharedUser"
						></Button>
					</div>
					<span class="mb-2 text-sm text-ink-gray-5">People with access</span>
					<div class="flex flex-col gap-1 overflow-y-auto">
						<div class="flex w-full items-center gap-2 py-1">
							<Avatar size="xl" label="You" :image="session.user.user_image" />
							<div class="flex flex-1 flex-col">
								<div class="leading-5">You</div>
								<div class="text-xs text-ink-gray-5">
									{{ session.user.email }}
								</div>
							</div>
							<Badge size="lg" theme="orange">Owner</Badge>
						</div>
						<div
							v-for="user in peopleWithAccess"
							:key="user.email"
							class="flex w-full items-center gap-2 py-1"
						>
							<Avatar size="xl" :label="user.full_name" :image="user.user_image" />
							<div class="flex flex-1 flex-col">
								<div class="leading-5">{{ user.full_name }}</div>
								<div class="text-xs text-ink-gray-5">{{ user.email }}</div>
							</div>
							<Button
								variant="ghost"
								icon="lucide-x"
								@click="peopleWithAccess.splice(peopleWithAccess.indexOf(user), 1)"
							></Button>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
