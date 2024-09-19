<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import UserSelector from '../components/UserSelector.vue'
import { createToast } from '../helpers/toasts'
import session from '../session'
import { ShareAccess, WorkbookSharePermission } from '../types/workbook.types'
import useUserStore, { User } from '../users/users'
import { Workbook, workbookKey } from './workbook'

const show = defineModel()

const userStore = useUserStore()
const selectedUserEmail = ref<string>('')

function shareWorkbook() {
	if (!selectedUserEmail.value) return
	permissionMap.value[selectedUserEmail.value] = 'view'
	selectedUserEmail.value = ''
}

type PermissionMap = Record<string, ShareAccess>
const permissionMap = ref<PermissionMap>({})
const accessOptions = (user_email: string) => [
	{ label: 'Can Edit', value: 'edit', onClick: () => (permissionMap.value[user_email] = 'edit') },
	{ label: 'Can View', value: 'view', onClick: () => (permissionMap.value[user_email] = 'view') },
	{
		label: 'Remove',
		value: 'remove',
		onClick: () => (permissionMap.value[user_email] = undefined),
	},
]

const workbook = inject(workbookKey) as Workbook
const workbookPermissions = ref<PermissionMap>({})
workbook.getSharePermissions().then((permissions) => {
	permissions.forEach((p: any) => {
		workbookPermissions.value[p.email] = p.access
		permissionMap.value[p.email] = p.access
	})
})

const userPermissions = computed(() => {
	return Object.keys(permissionMap.value)
		.map((email) => {
			const user = userStore.users.find((u) => u.email === email)
			if (!user) return null
			return {
				email,
				full_name: user.full_name,
				access: permissionMap.value[email],
			}
		})
		.filter(Boolean) as WorkbookSharePermission[]
})
const saveDisabled = computed(() => {
	return JSON.stringify(permissionMap.value) === JSON.stringify(workbookPermissions.value)
})
function updatePermissions() {
	workbook.updateSharePermissions(userPermissions.value)
	show.value = false
	createToast({
		title: 'Permissions updated',
		variant: 'success',
	})
}
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Share Workbook',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					disabled: saveDisabled,
					onClick: updatePermissions,
				},
			],
		}"
	>
		<template #body-content>
			<div class="-mb-8 flex flex-col gap-3 text-base">
				<div class="flex w-full gap-2">
					<div class="flex-1">
						<UserSelector
							v-model="selectedUserEmail"
							:hide-users="userPermissions.map((u) => u.email)"
						/>
					</div>
					<Button
						class="flex-shrink-0"
						variant="solid"
						label="Share"
						:disabled="!selectedUserEmail"
						@click="shareWorkbook"
					></Button>
				</div>

				<div class="flex flex-col gap-1 overflow-y-auto">
					<div
						v-for="user in userPermissions.filter((u) => u.access)"
						:key="user.email"
						class="flex w-full items-center gap-2 py-1"
					>
						<Avatar
							size="xl"
							:label="user.full_name"
							:image="userStore.getUser(user.email)?.user_image"
						/>
						<div class="flex flex-1 flex-col">
							<div class="leading-5">{{ user.full_name }}</div>
							<div class="text-xs text-gray-600">{{ user.email }}</div>
						</div>
						<Dropdown
							v-if="user.email !== session.user.email"
							class="flex-shrink-0"
							placement="right"
							:options="accessOptions(user.email)"
							:button="{
								iconRight: 'chevron-down',
								variant: 'ghost',
								label: user.access === 'edit' ? 'Can Edit' : 'Can View',
							}"
						/>
						<Button
							v-else
							variant="ghost"
							label="Owner"
							disabled
							class="flex-shrink-0"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
