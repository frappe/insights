<script setup lang="ts">
import { toast } from 'frappe-ui'
import { __ } from '../translation'
import { computed, inject, ref } from 'vue'
import UserSelector from '../components/UserSelector.vue'
import OrganizationAccessRow from './OrganizationAccessRow.vue'
import ShareUserRow from './ShareUserRow.vue'
import { showErrorToast } from '../helpers'
import session from '../session'
import { ShareAccess, WorkbookSharePermission } from '../types/workbook.types'
import useUserStore from '../users/users'
import type { Workbook } from './workbook'
import { workbookKey } from './workbook_key'

const show = defineModel()
const originalOrganizationAccess = ref<'view' | 'edit'>()
const organizationAccess = ref<'view' | 'edit'>()

const userStore = useUserStore()
const selectedUserEmail = ref<string>('')

function shareWorkbook() {
	if (!selectedUserEmail.value) return
	const email = selectedUserEmail.value
	const user = userStore.getUser(email)
	userInfo.value[email] = { full_name: user?.full_name || email, user_image: user?.user_image }
	permissionMap.value[email] = 'view'
	selectedUserEmail.value = ''
}

type PermissionMap = Record<string, ShareAccess>
const permissionMap = ref<PermissionMap>({})
const accessOptions = (user_email: string) => [
	{
		label: __('Can Edit'),
		value: 'edit',
		onClick: () => (permissionMap.value[user_email] = 'edit'),
	},
	{
		label: __('Can View'),
		value: 'view',
		onClick: () => (permissionMap.value[user_email] = 'view'),
	},
	{
		label: __('Remove'),
		value: 'remove',
		onClick: () => (permissionMap.value[user_email] = undefined),
	},
]

const workbook = inject(workbookKey) as Workbook
const workbookPermissions = ref<PermissionMap>({})

// who a share belongs to comes from the share itself, not from the roster -
// an owner may not be allowed to look up the people they shared with
type UserInfo = { full_name: string; user_image?: string }
const userInfo = ref<Record<string, UserInfo>>({})

workbook.getSharePermissions().then((permissions) => {
	permissions.user_permissions.forEach((p) => {
		workbookPermissions.value[p.email] = p.access
		permissionMap.value[p.email] = p.access
		userInfo.value[p.email] = { full_name: p.full_name, user_image: p.user_image }
	})
	originalOrganizationAccess.value = permissions.organization_access
	organizationAccess.value = permissions.organization_access
})

const userPermissions = computed(() => {
	return Object.keys(permissionMap.value).map((email) => {
		return {
			email,
			full_name: userInfo.value[email]?.full_name || email,
			user_image: userInfo.value[email]?.user_image,
			access: permissionMap.value[email],
		}
	}) as WorkbookSharePermission[]
})
const saveDisabled = computed(() => {
	return (
		JSON.stringify(permissionMap.value) === JSON.stringify(workbookPermissions.value) &&
		organizationAccess.value === originalOrganizationAccess.value
	)
})
function updatePermissions() {
	workbook
		.updateSharePermissions({
			user_permissions: userPermissions.value,
			organization_access: organizationAccess.value,
		})
		.then(() => {
			show.value = false
			toast.success(__('Permissions updated'))
		})
		.catch(showErrorToast)
}
</script>

<template>
	<Dialog
		v-model:open="show"
		:title="__('Manage Workbook Access')"
		:actions="[
			{
				label: __('Save'),
				variant: 'solid',
				disabled: saveDisabled,
				onClick: updatePermissions,
			},
		]"
	>
		<template #default>
			<div class="-mb-4 flex flex-col gap-3 text-base">
				<OrganizationAccessRow
					:access="organizationAccess"
					:options="[
						{
							label: __('Disabled'),
							onClick: () => (organizationAccess = undefined),
						},
						{
							label: __('Can View'),
							onClick: () => (organizationAccess = 'view'),
						},
						{
							label: __('Can Edit'),
							onClick: () => (organizationAccess = 'edit'),
						},
					]"
				/>
				<hr class="my-2 border-t border-outline-gray-1" />
				<div class="flex w-full gap-2">
					<div class="flex-1">
						<UserSelector
							v-model="selectedUserEmail"
							placeholder="Search by name or email"
							allow-custom-email
							:hide-users="
								userPermissions.filter((u) => u.access).map((u) => u.email)
							"
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
					<ShareUserRow
						v-for="user in userPermissions.filter((u) => u.access)"
						:key="user.email"
						:full-name="user.full_name"
						:email="user.email"
						:image="user.user_image"
						:access="user.email === session.user.email ? 'owner' : user.access"
						:options="accessOptions(user.email)"
					/>

					<div
						v-if="userPermissions.filter((u) => u.access).length === 0"
						class="rounded-4 border border-dashed border-outline-gray-2 px-32 py-6 text-center text-sm text-ink-gray-4"
					>
						{{
							organizationAccess
								? `All users in your organization can ${organizationAccess} this workbook`
								: 'Only you have access to this workbook'
						}}
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
