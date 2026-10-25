<script setup lang="ts">
import { Alert, toast, Tooltip } from 'frappe-ui'
import { computed, inject, ref, watch } from 'vue'
import UserSelector from '../components/UserSelector.vue'
import VisibilitySelector from '../components/VisibilitySelector.vue'
import { copy, copyToClipboard } from '../helpers'
import session from '../session'
import { Visibility } from '../types/workbook.types'
import useUserStore from '../users/users'
import ShareUserRow from '../workbook/ShareUserRow.vue'
import { Dashboard } from './dashboard'
import { rolesWithoutReadLines, type RolesWithoutRead } from './roles_without_read'
import { __ } from '../translation'

const show = defineModel()

const dashboard = inject('dashboard') as Dashboard

const visibility = ref<Visibility>(dashboard.doc.visibility || 'Private')
const visibleToRoles = ref((dashboard.doc.visible_to_roles || []).map((r) => r.role))
const peopleWithAccess = ref(copy(dashboard.doc.people_with_access))

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
		visibility: dashboard.doc.visibility || 'Private',
		visible_to_roles: (dashboard.doc.visible_to_roles || []).map((r) => r.role),
		people_with_access: dashboard.doc.people_with_access.map((u) => u.email),
	}
	return JSON.stringify(prev) !== JSON.stringify(next)
})

// The chosen roles that can't read what the dashboard's charts read. Save
// names them once, and the next Save saves anyway.
const rolesWithoutRead = ref<RolesWithoutRead>()
watch([visibility, visibleToRoles], () => (rolesWithoutRead.value = undefined), { deep: true })
const warning = computed(() => rolesWithoutReadLines(rolesWithoutRead.value || {}))

// the roles this Save adds: those already saved were checked when they were
const addedRoles = computed(() => {
	if (visibility.value !== 'Roles') return []
	const saved =
		dashboard.doc.visibility === 'Roles'
			? (dashboard.doc.visible_to_roles || []).map((r) => r.role)
			: []
	return visibleToRoles.value.filter((role) => !saved.includes(role))
})

async function saveChanges() {
	if (!rolesWithoutRead.value && addedRoles.value.length) {
		// a check that failed has shown its error, and saves nothing unchecked
		const answer = await dashboard
			.call('get_roles_without_read', { roles: addedRoles.value })
			.catch(() => undefined)
		if (!answer) return
		rolesWithoutRead.value = answer
		if (warning.value.length) return
	}
	dashboard.doc.visibility = visibility.value
	dashboard.doc.visible_to_roles = visibleToRoles.value.map((role) => ({ role }))
	await dashboard.save()
	await dashboard.updateAccess({
		people_with_access: peopleWithAccess.value.map((u) => u.email),
	})
	toast.success(__('Dashboard Access Updated'))
	show.value = false
}

const selectedUserEmail = ref<string>('')
const userStore = useUserStore()

const owner = computed(() =>
	dashboard.doc.owner === session.user.email
		? {
				full_name: session.user.full_name || session.user.email,
				user_image: session.user.user_image,
		  }
		: {
				full_name: userStore.getName(dashboard.doc.owner) || dashboard.doc.owner,
				user_image: userStore.getImage(dashboard.doc.owner),
		  },
)
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
				label: warning.length ? __('Save anyway') : __('Save'),
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

				<p v-if="visibility === 'Public'" class="-mt-2 text-sm text-ink-gray-5">
					{{
						__(
							"Guests have no permissions of their own, so every chart on a public dashboard runs as its owner and shows them the rows its owner can see. Each chart's owner turns on Run as owner in the chart's share dialog.",
						)
					}}
				</p>

				<Alert
					v-if="warning.length"
					theme="amber"
					:title="warning.join(' ')"
					:description="
						__(
							'People with only these roles see Not Permitted in place of the charts that read them.',
						)
					"
				/>

				<hr class="my-1 border-t border-outline-gray-1" />

				<div class="flex flex-col">
					<div class="mb-4 flex w-full gap-2">
						<div class="flex-1">
							<UserSelector
								v-model="selectedUserEmail"
								placeholder="Search by name or email"
								:hide-users="peopleWithAccess.map((u) => u.email)"
								shares-with-roles
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
						<ShareUserRow
							:full-name="owner.full_name"
							:email="dashboard.doc.owner"
							:image="owner.user_image"
							access="owner"
						/>
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
