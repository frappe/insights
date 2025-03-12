<template>
	<div>
		<Dropdown :options="userDropdownOptions">
			<template v-slot="{ open }">
				<button
					class="flex h-12 items-center rounded-md py-2 duration-300 ease-in-out"
					:class="
						props.isCollapsed
							? 'w-auto px-0'
							: open
							? 'w-52 bg-white px-2 shadow-sm'
							: 'w-52 px-2 hover:bg-gray-200'
					"
				>
					<img
						src="../assets/insights-logo-new.svg"
						alt="logo"
						class="h-8 w-8 flex-shrink-0 rounded"
					/>
					<div
						class="flex flex-1 flex-col text-left duration-300 ease-in-out"
						:class="
							props.isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<div class="text-base font-medium leading-none text-gray-900">Insights</div>
						<div class="mt-1 text-sm leading-none text-gray-700">
							{{ session.user.full_name }}
						</div>
					</div>
					<div
						class="duration-300 ease-in-out"
						:class="
							props.isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<ChevronDown class="h-4 w-4 text-gray-600" aria-hidden="true" />
					</div>
				</button>
			</template>
		</Dropdown>

		<Dialog
			v-model="showSwitchToV2Dialog"
			:options="{
				title: 'Switch to Insights v2',
				actions: [
					{
						label: 'Continue',
						variant: 'solid',
						onClick: openInsightsV2,
					},
				],
			}"
		>
			<template #body-content>
				<div class="prose prose-sm mb-4">
					<p>Switch to the old version of Insights?</p>
				</div>
				<FormControl
					type="checkbox"
					label="Set Insights v2 as default"
					:modelValue="session.user.default_version === 'v2'"
					@update:modelValue="session.user.default_version = $event ? 'v2' : ''"
				/>
			</template>
		</Dialog>

		<Dialog
			v-model="showLoginToFCDialog"
			:options="{
				title: 'Login to Frappe Cloud?',
				message: 'Are you sure you want to login to your Frappe Cloud dashboard?',
				actions: [
					{
						label: 'Confirm',
						variant: 'solid',
						loading: loggingInToFC,
						onClick() {
							loginToFC()
							showLoginToFCDialog.value = false
						},
					},
				],
			}"
		/>
	</div>
</template>

<script setup lang="ts">
import { call, Dropdown } from 'frappe-ui'
import { ChevronDown, HelpCircle, LogOut, MessageCircle, ToggleRight } from 'lucide-vue-next'
import { h, ref } from 'vue'
import { showErrorToast, waitUntil } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import session from '../session'
import FrappeCloudIcon from './Icons/FrappeCloudIcon.vue'

const props = defineProps<{ isCollapsed?: boolean }>()

const showSwitchToV2Dialog = ref(false)
const showLoginToFCDialog = ref(false)

const userDropdownOptions = ref([
	{
		label: 'Documentation',
		icon: h(HelpCircle),
		onClick: () => window.open('https://docs.frappe.io/insights', '_blank'),
	},
	{
		label: 'Join Telegram Group',
		icon: h(MessageCircle),
		onClick: () => window.open('https://t.me/frappeinsights', '_blank'),
	},
	{
		label: 'Log out',
		icon: h(LogOut),
		onClick: () =>
			confirmDialog({
				title: 'Log out',
				message: 'Are you sure you want to log out?',
				onSuccess: session.logout,
			}),
	},
])

waitUntil(() => session.initialized).then(() => {
	if (session.user.is_v2_instance) {
		userDropdownOptions.value.splice(userDropdownOptions.value.length - 2, 0, {
			label: 'Switch to Insights v2',
			icon: h(ToggleRight),
			onClick: () => (showSwitchToV2Dialog.value = true),
		})
	}

	if (session.user.is_admin) {
		userDropdownOptions.value.splice(userDropdownOptions.value.length - 2, 0, {
			label: 'Switch to Desk',
			icon: h(ToggleRight),
			onClick: () => window.open('/app', '_blank'),
		})
	}
})

if (window.is_fc_site) {
	userDropdownOptions.value.splice(userDropdownOptions.value.length - 1, 0, {
		icon: h(FrappeCloudIcon),
		label: 'Login to Frappe Cloud',
		onClick: () => (showLoginToFCDialog.value = true),
	})
}

function openInsightsV2() {
	session.updateDefaultVersion(session.user.default_version).then(() => {
		window.location.href = '/insights_v2'
	})
}

const loggingInToFC = ref(false)
function loginToFC() {
	loggingInToFC.value = true
	call('frappe.integrations.frappe_providers.frappecloud_billing.current_site_info')
		.then((data: any) => {
			if (!data.base_url || !data.site_name) {
				throw new Error('Invalid response')
			}
			window.open(`${data.base_url}/dashboard/sites/${data.site_name}`, '_blank')
		})
		.catch(showErrorToast)
		.finally(() => {
			loggingInToFC.value = false
		})
}
</script>
