<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import session from '../session'
import useUserStore from '../users'
import { createToast } from '../helpers/toasts'
import { ShareAccess, WorkbookSharePermission } from '../types/workbook.types'
import { Workbook, workbookKey } from './workbook'

const show = defineModel()
const searchTxt = ref('')
const userStore = useUserStore()

const filteredUsers = computed(() => {
	return userStore.users
		.filter((user) => {
			if (!searchTxt.value) return true
			return (
				user.full_name.toLowerCase().includes(searchTxt.value.toLowerCase()) ||
				user.email.toLowerCase().includes(searchTxt.value.toLowerCase())
			)
		})
		.filter((user) => {
			return !permissionMap.value[user.email]
		})
		.map((user) => {
			return {
				...user,
				label: user.full_name,
				value: user.email,
				description: user.email,
			}
		})
})

type User = typeof userStore.users[0]
const selectedUser = ref<User | null>(null)
function shareWorkbook() {
	if (!selectedUser.value) return
	permissionMap.value[selectedUser.value.email] = 'view'
	selectedUser.value = null
	searchTxt.value = ''
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
						<Autocomplete
							v-model="selectedUser"
							:hide-search="true"
							:options="filteredUsers"
							:autofocus="false"
							@update:modelValue="searchTxt = $event.email"
						>
							<template #target="{ open }">
								<FormControl
									class="w-full"
									type="text"
									placeholder="Search by email or name"
									autocomplete="off"
									v-model="searchTxt"
									@update:modelValue="open"
									@focus="open"
								/>
							</template>

							<template #item-prefix="{ option }">
								<Avatar
									size="sm"
									:label="option.label"
									:image="option.user_image"
								/>
							</template>
						</Autocomplete>
					</div>
					<Button
						class="flex-shrink-0"
						variant="solid"
						label="Share"
						:disabled="selectedUser === null"
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
