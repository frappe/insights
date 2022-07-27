<template>
	<div class="fixed inset-y-0 flex w-64 flex-col bg-gray-50" v-if="currentRoute">
		<div class="flex flex-grow flex-col overflow-y-auto p-6 pl-4 pr-2">
			<div class="flex flex-shrink-0 items-center">
				<FrappeInsightsLogo />
			</div>
			<div class="mt-4 flex flex-grow flex-col">
				<nav class="flex-1 space-y-1 pb-4 text-base">
					<router-link
						v-for="route in sidebarItems"
						:key="route.path"
						:to="route.path"
						:class="[
							route.current
								? 'bg-gray-200 text-gray-800'
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
			<div
				class="flex flex-shrink-0 border-gray-200 px-2 pt-4 text-sm font-light text-gray-500"
			>
				{{ appVersion }}
			</div>
		</div>
	</div>
</template>

<script setup>
import FrappeInsightsLogo from '@/components/Icons/FrappeInsights.vue'

import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { createResource } from 'frappe-ui'

const sidebarItems = ref([
	{
		path: '/dashboard',
		label: 'Dashboards',
		icon: 'bar-chart-2',
		name: 'Dashboard',
		current: false,
	},
	// {
	// 	path: '/data-source',
	// 	label: 'Data Sources',
	// 	icon: 'database',
	// 	name: 'Data Source',
	// },
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

const route = useRoute()
const currentRoute = computed(() => {
	sidebarItems.value.forEach((item) => {
		item.current = item.path == route.path
	})
	return route.path
})

const getAppVersion = createResource({
	method: 'insights.api.get_app_version',
	initialData: '0.0.0',
})
getAppVersion.fetch()
const appVersion = computed(() => {
	return `Insights v${getAppVersion.data}`
})
</script>
