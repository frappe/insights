<template>
	<div class="fixed inset-y-0 flex w-64 flex-col" v-if="current_route">
		<div class="flex flex-grow flex-col overflow-y-auto p-6 pr-0">
			<div class="flex flex-shrink-0 items-center px-1">
				<FrappeInsights />
			</div>
			<div class="mt-4 flex flex-grow flex-col">
				<nav class="flex-1 space-y-1 pb-4 text-base">
					<router-link
						v-for="route in routes"
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
				Insights Beta v0.0.1
			</div>
		</div>
	</div>
</template>

<script>
import FrappeInsights from '@/components/Icons/FrappeInsights.vue'

export default {
	name: 'Sidebar',
	components: {
		FrappeInsights,
	},
	data() {
		return {
			routes: [
				{
					path: '/dashboard',
					label: 'Dashboards',
					icon: 'bar-chart-2',
					name: 'Dashboard',
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
				},
				{
					path: '/settings',
					label: 'Settings',
					icon: 'settings',
					name: 'Settings',
				},
			],
		}
	},
	computed: {
		current_route() {
			this.routes.forEach((route) => {
				if (
					route.path == this.$route.path ||
					(route.path != '/' && this.$route.path.includes(route.path)) // sub-route
				) {
					route.current = true
				} else {
					route.current = false
				}
			})
			return this.$route.path
		},
	},
}
</script>
