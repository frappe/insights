<template>
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
</template>

<script setup lang="ts">
import { Dropdown } from 'frappe-ui'
import { ChevronDown } from 'lucide-vue-next'
import { confirmDialog } from '../helpers/confirm_dialog'
import session from '../session'

const props = defineProps<{ isCollapsed: boolean }>()

const userDropdownOptions = [
	{
		icon: 'log-out',
		label: 'Log out',
		onClick: () =>
			confirmDialog({
				title: 'Log out',
				message: 'Are you sure you want to log out?',
				onSuccess: session.logout,
			}),
	},
]
</script>
