<script setup lang="tsx">
import { useTimeAgo } from '@vueuse/core'
import { Avatar, Breadcrumbs, ListView } from 'frappe-ui'
import { PlusIcon, SearchIcon, XIcon } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import IndicatorIcon from '../components/Icons/IndicatorIcon.vue'
import session from '../session'
import useUserStore, { User } from './users'

const userStore = useUserStore()
userStore.getUsers()

const searchQuery = ref('')
const filteredUsers = computed(() => {
	if (!searchQuery.value) {
		return userStore.users
	}
	return userStore.users.filter(
		(user) =>
			user.full_name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
			user.email.toLowerCase().includes(searchQuery.value.toLowerCase())
	)
})

const listOptions = ref({
	columns: [
		{
			label: 'User',
			key: 'full_name',
			prefix: (props: any) => {
				const user = props.row as User
				return <Avatar size="md" label={user.full_name} image={user.user_image} />
			},
		},
		{
			label: 'Status',
			key: 'enabled',
			getLabel: (props: any) => {
				const user = props.row as User
				if (user.invitation_status) {
					return user.invitation_status === 'Pending'
						? 'Invitation Sent'
						: 'Invitation Expired'
				}
				return props.row.enabled ? 'Enabled' : 'Disabled'
			},
			prefix: (props: any) => {
				let color
				const user = props.row as User
				if (user.invitation_status) {
					color =
						user.invitation_status === 'Pending' ? 'text-yellow-500' : 'text-red-500'
				} else {
					color = props.row.enabled ? 'text-green-500' : 'text-gray-500'
				}
				return <IndicatorIcon class={color} />
			},
		},
		{
			label: 'Email',
			key: 'email',
		},
		{
			label: 'Last Active',
			key: 'last_active',
			getLabel: (props: any) => {
				if (!props.row.last_active) {
					return ''
				}
				return useTimeAgo(props.row.last_active).value
			},
		},
	],
	rows: filteredUsers,
	rowKey: 'email',
	options: {
		showTooltip: false,
		emptyState: {
			title: 'No users.',
			description: 'No users to display.',
			button: session.user.is_admin
				? {
						label: 'Invite User',
						variant: 'solid',
						onClick: () => (showInviteUserDialog.value = true),
				  }
				: undefined,
		},
	},
})

const showInviteUserDialog = ref(false)
const emailsToInvite = ref<string[]>([])
const emailsTxt = ref('')
watch(emailsTxt, extractEmails)

function extractEmails(emails: string) {
	const lastChar = emails.slice(-1)
	if (lastChar != ' ' && lastChar != ',') {
		emailsTxt.value = emails
		return
	}

	const newEmails = emails
		.split(/,|\s/)
		.filter((email) => email)
		.filter((email) => !emailsToInvite.value.includes(email))
	emailsToInvite.value = [...emailsToInvite.value, ...newEmails]
	emailsTxt.value = ''
}

const areAllEmailsValid = computed(() => {
	if (!emailsToInvite.value.length && isValidEmail(emailsTxt.value)) {
		return true
	}
	if (!emailsToInvite.value.length) {
		return false
	}
	return emailsToInvite.value.every((email) => {
		return isValidEmail(email)
	})
})

function isValidEmail(email: string) {
	return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function sendInvitation() {
	if (!areAllEmailsValid.value) {
		return
	}
	if (!emailsToInvite.value.length) {
		emailsToInvite.value = [emailsTxt.value]
	}
	userStore.inviteUsers(emailsToInvite.value)
	emailsToInvite.value = []
	showInviteUserDialog.value = false
}

document.title = 'Users | Insights'
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: 'Users', route: '/users' }]" />
		<div class="flex items-center gap-2">
			<Button
				v-if="session.user.is_admin"
				label="Invite User"
				variant="solid"
				@click="showInviteUserDialog = true"
			>
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
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
		v-model="showInviteUserDialog"
		:options="{
			title: 'Invite User',
			actions: [
				{
					label: 'Send Invitation',
					variant: 'solid',
					disabled: !areAllEmailsValid,
					loading: userStore.sendingInvitation,
					onClick: sendInvitation,
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<div class="flex flex-wrap gap-1 rounded bg-gray-100 p-0.5">
					<Button
						v-for="(email, idx) in emailsToInvite"
						:key="email"
						:label="email"
						variant="outline"
						class="shadow-sm"
					>
						<template #suffix>
							<XIcon
								class="h-4"
								stroke-width="1.5"
								@click.stop="() => emailsToInvite.splice(idx, 1)"
							/>
						</template>
					</Button>
					<div class="min-w-[10rem] flex-1">
						<input
							type="text"
							autocomplete="off"
							placeholder="Enter email address"
							v-model="emailsTxt"
							@keydown.enter.capture.stop="extractEmails(`${emailsTxt} `)"
							class="h-7 w-full rounded border-none bg-gray-100 py-1.5 pl-2 pr-2 text-base text-gray-800 placeholder-gray-500 transition-colors focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
