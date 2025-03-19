<script setup lang="ts">
import { Badge, Tooltip } from 'frappe-ui'
import { computed, inject, ref, unref } from 'vue'
import UserSelector from '../components/UserSelector.vue'
import { copy, copyToClipboard } from '../helpers'
import session from '../session'
import { DropdownOption } from '../types/query.types'
import useUserStore from '../users/users'
import { Dashboard } from './dashboard'
import { createToast } from '../helpers/toasts'

const show = defineModel()

const dashboard = inject('dashboard') as Dashboard

const isPublic = ref(unref(dashboard.doc.is_public))
const peopleWithAccess = ref(copy(dashboard.doc.people_with_access))
const organizationAccess = ref(unref(dashboard.doc.is_shared_with_organization))

const shareLink = computed(() => dashboard.getShareLink())
const iFrameLink = computed(() => {
	return `<iframe src="${shareLink.value}" width="100%" height="100%" frameborder="0"></iframe>`
})

const hasChanged = computed(() => {
	const prev = {
		is_public: isPublic.value,
		people_with_access: peopleWithAccess.value.map((u) => u.email),
		is_shared_with_organization: organizationAccess.value,
	}
	const next = {
		is_public: dashboard.doc.is_public,
		people_with_access: dashboard.doc.people_with_access.map((u) => u.email),
		is_shared_with_organization: dashboard.doc.is_shared_with_organization,
	}
	return JSON.stringify(prev) !== JSON.stringify(next)
})

function saveChanges() {
	dashboard.updateAccess({
		is_public: isPublic.value,
		is_shared_with_organization: organizationAccess.value,
		people_with_access: peopleWithAccess.value.map((u) => u.email),
	})
	createToast({
		variant: 'success',
		title: 'Dashboard Access Updated',
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

const generalAccess = computed({
	get: () => {
		if (isPublic.value) return 'anyone'
		if (organizationAccess.value) return 'organization'
		return 'specific'
	},
	set: (option: DropdownOption) => {
		isPublic.value = option.value == 'anyone'
		organizationAccess.value = option.value == 'organization'
	},
})
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Share Dashboard',
			actions: [
				{
					label: 'Done',
					variant: 'solid',
					disabled: !hasChanged,
					onClick: saveChanges,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-3 text-base">
				<div class="space-y-4">
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
						<span class="mb-2 text-sm text-gray-600">People with access</span>
						<div class="flex flex-col gap-1 overflow-y-auto">
							<div class="flex w-full items-center gap-2 py-1">
								<Avatar size="xl" label="You" :image="session.user.user_image" />
								<div class="flex flex-1 flex-col">
									<div class="leading-5">You</div>
									<div class="text-xs text-gray-600">
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
								<Avatar
									size="xl"
									:label="user.full_name"
									:image="user.user_image"
								/>
								<div class="flex flex-1 flex-col">
									<div class="leading-5">{{ user.full_name }}</div>
									<div class="text-xs text-gray-600">{{ user.email }}</div>
								</div>
								<Button
									variant="ghost"
									icon="x"
									@click="
										peopleWithAccess.splice(peopleWithAccess.indexOf(user), 1)
									"
								></Button>
							</div>
						</div>
					</div>

					<hr class="my-2 border-t border-gray-200" />

					<div class="flex flex-col gap-2">
						<span class="text-sm text-gray-600">General Access</span>
						<div class="flex gap-2">
							<div class="flex-1">
								<Autocomplete
									placeholder="Select an option"
									:hide-search="true"
									v-model="generalAccess"
									:options="[
										{
											label: 'Anyone with the link can view',
											value: 'anyone',
										},
										{
											label: 'Anyone in the organization can view',
											value: 'organization',
										},
										{
											label: 'Specific people can view',
											value: 'specific',
										},
									]"
								>
								</Autocomplete>
							</div>
							<Tooltip text="Copy Link" :hoverDelay="0.1">
								<Button icon="link-2" @click="copyToClipboard(shareLink)"> </Button>
							</Tooltip>
							<Tooltip text="Copy Embed" :hoverDelay="0.1">
								<Button icon="code" @click="copyToClipboard(iFrameLink)"> </Button>
							</Tooltip>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
