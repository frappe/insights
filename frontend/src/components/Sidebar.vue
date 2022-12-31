<template>
	<div class="flex w-60 flex-col bg-gray-50" v-if="currentRoute">
		<div class="flex flex-grow flex-col overflow-y-auto p-4 pl-4 pr-2">
			<div class="flex h-6 flex-shrink-0 items-end text-sm text-gray-500">
				<FrappeInsightsLogo />
				<span class="ml-1">{{ appVersion }}</span>
			</div>
			<div class="mt-4 flex flex-grow flex-col">
				<nav class="flex-1 space-y-1 pb-4 text-base">
					<router-link
						v-for="route in sidebarItems"
						:key="route.path"
						:to="route.path"
						:class="[
							route.current
								? 'bg-gray-200/70'
								: 'text-gray-600 hover:bg-gray-50 hover:text-gray-800',
							'group flex items-center rounded-md px-2 py-2 font-medium',
						]"
						aria-current="page"
					>
						<FeatherIcon
							:name="route.icon"
							:class="[
								route.current
									? 'text-gray-600'
									: 'text-gray-500 group-hover:text-gray-600',
								'mr-3 h-4 w-4 flex-shrink-0',
							]"
						/>
						{{ route.label }}
					</router-link>
				</nav>
			</div>

			<div class="flex items-center text-base text-gray-600">
				<Avatar :label="auth.user.full_name" :imageURL="auth.user.user_image" />
				<span class="ml-2">{{ auth.user.full_name }}</span>
				<Button icon="log-out" appearance="minimal" class="ml-auto" @click="auth.logout" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { Avatar } from 'frappe-ui'
import FrappeInsightsLogo from '@/components/Icons/FrappeInsights.vue'

import { ref, computed } from 'vue'
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
		path: '/teams',
		label: 'Teams',
		icon: 'users',
		name: 'Teams',
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

const route = useRoute()
const currentRoute = computed(() => {
	sidebarItems.value.forEach((item) => {
		item.current = route.path.includes(item.path)
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
</script>
