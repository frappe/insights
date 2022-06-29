<template>
	<div class="fixed inset-y-0 flex w-64 flex-col" v-if="current_route">
		<div class="flex flex-grow flex-col overflow-y-auto border-r border-gray-200 bg-white pt-5">
			<div class="flex flex-shrink-0 items-center px-5">
				<FrappeInsightsLogo />
			</div>
			<div class="mt-5 flex flex-grow flex-col">
				<nav class="flex-1 space-y-1 px-2 pb-4">
					<router-link
						v-for="route in routes"
						:key="route.path"
						:to="route.path"
						:class="[
							route.current
								? 'bg-gray-100 text-gray-900'
								: 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
							'group flex items-center rounded-md px-2 py-2 text-sm font-medium',
						]"
						aria-current="page"
					>
						<FeatherIcon
							:name="route.icon"
							:class="[
								route.current ? 'text-gray-500' : 'text-gray-400 group-hover:text-gray-500',
								'mr-3 h-4 w-4 flex-shrink-0',
							]"
						/>
						{{ route.label }}
					</router-link>
				</nav>
			</div>
		</div>
	</div>
</template>

<script>
import FrappeInsightsLogo from '@/components/FrappeInsightsLogo.vue'

export default {
	name: 'Sidebar',
	components: {
		FrappeInsightsLogo,
	},
	data() {
		return {
			routes: [
				{
					path: '/',
					label: 'Dashboards',
					icon: 'bar-chart-2',
					name: 'Dashboard',
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
