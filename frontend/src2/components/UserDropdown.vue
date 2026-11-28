<template>
	<div>
		<Dropdown :options="userDropdownOptions">
			<template v-slot="{ open }">
				<button
					class="flex h-12 items-center rounded-5 py-2 duration-300 ease-in-out"
					:class="
						props.isCollapsed
							? 'w-auto px-0'
							: open
							  ? 'w-52 bg-surface-elevation-2 px-2 shadow-sm'
							  : 'w-52 px-2 hover:bg-surface-gray-3'
					"
				>
					<img
						src="../assets/insights-logo-new.svg"
						alt="logo"
						class="h-8 w-8 flex-shrink-0 rounded-4"
					/>
					<div
						class="flex flex-1 flex-col text-left duration-300 ease-in-out"
						:class="
							props.isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<div class="text-base-medium leading-none text-ink-gray-8">Insights</div>
						<div class="mt-1 text-sm leading-none text-ink-gray-6">
							{{
								session.user.full_name == 'Administrator'
									? __(session.user.full_name)
									: session.user.full_name
							}}
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
						<ChevronDown class="h-4 w-4 text-ink-gray-5" aria-hidden="true" />
					</div>
				</button>
			</template>
		</Dropdown>

		<Dialog
			v-model:open="showLoginToFCDialog"
			:title="__('Login to Frappe Cloud?')"
			:message="__('Are you sure you want to login to your Frappe Cloud dashboard?')"
			:actions="[
				{
					label: __('Confirm'),
					variant: 'solid',
					loading: loggingInToFC,
					onClick: confirmLoginToFC,
				},
			]"
		/>
	</div>
</template>

<script setup lang="ts">
import { Dropdown } from 'frappe-ui'
import { ChevronDown } from 'lucide-vue-next'
import session from '../session'
import { __ } from '../translation'
import { loggingInToFC, loginToFC, showLoginToFCDialog, useUserMenuOptions } from './user_menu'

const props = defineProps<{ isCollapsed?: boolean }>()

const userDropdownOptions = useUserMenuOptions()

function confirmLoginToFC() {
	loginToFC()
	showLoginToFCDialog.value = false
}
</script>
