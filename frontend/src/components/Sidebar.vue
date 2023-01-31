<template>
	<div class="flex w-16 flex-shrink-0 flex-col bg-gray-50 xl:w-60" v-if="currentRoute">
		<div class="flex flex-grow flex-col overflow-y-auto p-4">
			<div class="hidden flex-shrink-0 items-end text-sm text-gray-500 xl:flex">
				<img src="../assets/insights-logo.svg" class="h-7" />
				<span class="ml-1 mb-0.5 font-mono">{{ appVersion }}</span>
			</div>
			<div class="flex xl:hidden">
				<img src="../assets/insights-icon.svg" class="rounded-md" />
			</div>

			<div class="mt-4 flex flex-col">
				<nav class="flex-1 space-y-1 pb-4 text-base">
					<Tooltip
						v-for="route in sidebarItems"
						:key="route.path"
						placement="right"
						:hoverDelay="0.1"
						class="w-full"
					>
						<template #body>
							<div
								class="w-fit rounded-lg border border-gray-100 bg-gray-800 px-2 py-1 text-xs text-white shadow-xl"
							>
								{{ route.label }}
							</div>
						</template>

						<router-link
							:to="route.path"
							:class="[
								route.current
									? 'bg-gray-200/70'
									: 'text-gray-600 hover:bg-gray-50 hover:text-gray-800',
								'group -mx-1 flex items-center justify-center rounded-md p-2 font-medium xl:justify-start',
							]"
							aria-current="page"
						>
							<FeatherIcon
								:name="route.icon"
								:class="[
									route.current
										? 'text-gray-600'
										: 'text-gray-500 group-hover:text-gray-600',
									'mr-0 h-5 w-5 flex-shrink-0 xl:mr-3 xl:h-4 xl:w-4',
								]"
							/>
							<span class="hidden xl:inline-block">{{ route.label }}</span>
						</router-link>
					</Tooltip>
				</nav>
			</div>

			<div class="-mx-2 mt-auto flex items-center text-base text-gray-600 xl:mx-0">
				<Dropdown
					placement="left"
					:options="[
						{
							label: 'Documentation',
							icon: 'help-circle',
							handler: () => open('https://frappeinsights.com/docs'),
						},
						auth.user.is_admin
							? {
									label: 'Switch to Desk',
									icon: 'grid',
									handler: () => open('/app'),
							  }
							: null,
						{
							label: 'Logout',
							icon: 'log-out',
							handler: () => auth.logout(),
						},
					]"
				>
					<template v-slot="{ open }">
						<button
							class="flex w-full items-center space-x-2 rounded-md p-2 text-left text-base font-medium"
							:class="open ? 'bg-gray-300' : 'hover:bg-gray-200'"
						>
							<Avatar
								:label="auth.user.full_name"
								:imageURL="auth.user.user_image"
								size="md"
							/>
							<span
								class="ml-2 hidden overflow-hidden text-ellipsis whitespace-nowrap xl:inline"
							>
								{{ auth.user.full_name }}
							</span>
							<FeatherIcon name="chevron-down" class="hidden h-4 w-4 xl:inline" />
						</button>
					</template>
				</Dropdown>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Avatar } from 'frappe-ui'

import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { createResource } from 'frappe-ui'
import auth from '@/utils/auth'
import { getOnboardingStatus } from '@/utils/onboarding'

const sidebarItems = ref([
	{
		path: '/dashboard',
		label: 'Dashboards',
		icon: 'bar-chart-2',
		name: 'Dashboard',
		current: false,
	},
	{
		path: '/data-source',
		label: 'Data Sources',
		icon: 'database',
		name: 'Data Source',
	},
	{
		path: '/query',
		label: 'Queries',
		icon: 'columns',
		name: 'QueryBuilder',
		current: false,
	},
	{
		path: '/settings',
		label: 'Settings',
		icon: 'settings',
		name: 'Settings',
		current: false,
	},
])

getOnboardingStatus().then((onboardingComplete) => {
	if (!onboardingComplete) {
		// add onboarding item as first item in sidebar
		sidebarItems.value.unshift({
			path: '/get-started',
			label: 'Get Started',
			icon: 'star',
			name: 'GetStarted',
			current: false,
		})
	}
})
watch(
	() => auth.user.is_admin,
	(isAdmin) => {
		if (isAdmin) {
			// add users & teams item after settings item
			if (sidebarItems.value.find((item) => item.name === 'Teams')) {
				return
			}
			const settingsIndex = sidebarItems.value.findIndex((item) => item.name === 'Settings')
			sidebarItems.value.splice(settingsIndex, 0, {
				path: '/users',
				label: 'Users',
				icon: 'user',
				name: 'Users',
				current: false,
			})
			sidebarItems.value.splice(settingsIndex + 1, 0, {
				path: '/teams',
				label: 'Teams',
				icon: 'users',
				name: 'Teams',
				current: false,
			})
		}
	}
)

const route = useRoute()
const currentRoute = computed(() => {
	sidebarItems.value.forEach((item) => {
		// check if /<route> or /<route>/<id> is in sidebar item path
		item.current = route.path.match(new RegExp(`^${item.path}(/|$)`))
	})
	return route.path
})

const getAppVersion = createResource({
	url: 'insights.api.get_app_version',
	initialData: '0.0.0',
	auto: true,
})
const appVersion = computed(() => {
	return `v${getAppVersion.data}`
})
const open = (url) => window.open(url, '_blank')
</script>
