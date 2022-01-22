<template>
	<div class="h-full">
		<nav class="bg-white shadow-sm">
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<div class="flex justify-between h-16">
					<div class="flex">
						<div class="flex-shrink-0 flex items-center">
							<FrappeAnalyticsLogo />
						</div>
						<div class="hidden sm:-my-px sm:ml-6 sm:flex sm:space-x-8">
							<!-- Current: "border-indigo-500 text-gray-900", Default: "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300" -->

							<router-link
								to="/"
								class="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
								aria-current="page"
							>Dashboards</router-link>

							<router-link
								to="reports"
								class="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
								aria-current="page"
							>Reports</router-link>

							<router-link
								to="query-builder"
								class="border-indigo-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
								aria-current="page"
							>Builder</router-link>

							<router-link
								to="settings"
								class="border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
								aria-current="page"
							>Settings</router-link>
						</div>
					</div>
				</div>
			</div>
		</nav>

		<router-view />
	</div>
</template>

<script>
import FrappeAnalyticsLogo from '@/components/FrappeAnalyticsLogo.vue';

export default {
	name: 'App',
	components: {
		FrappeAnalyticsLogo
	},
}
</script>
