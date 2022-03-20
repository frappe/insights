<template>
	<div class="flex h-screen select-none flex-col font-sans">
		<nav class="bg-white shadow-sm">
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div class="flex h-16 justify-between">
					<div class="flex">
						<div class="flex flex-shrink-0 items-center">
							<FrappeAnalyticsLogo />
						</div>
						<div class="hidden sm:-my-px sm:ml-6 sm:flex sm:space-x-8">
							<!-- Current: "border-indigo-500 text-gray-900", Default: "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300" -->

							<router-link
								to="/"
								class="inline-flex items-center border-b-2 border-transparent px-1 pt-1 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700"
								aria-current="page"
								>Dashboards</router-link
							>

							<router-link
								to="reports"
								class="inline-flex items-center border-b-2 border-transparent px-1 pt-1 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700"
								aria-current="page"
								>Reports</router-link
							>

							<router-link
								to="query-builder"
								class="inline-flex items-center border-b-2 border-indigo-500 px-1 pt-1 text-sm font-medium text-gray-900"
								aria-current="page"
								>Builder</router-link
							>

							<router-link
								to="settings"
								class="inline-flex items-center border-b-2 border-transparent px-1 pt-1 text-sm font-medium text-gray-500 hover:border-gray-300 hover:text-gray-700"
								aria-current="page"
								>Settings</router-link
							>
						</div>
					</div>
				</div>
			</div>
		</nav>

		<router-view class="flex flex-1 flex-col" />
		<NotificationToasts />
	</div>
</template>

<script>
import { NotificationToasts } from 'frappe-ui'
import FrappeAnalyticsLogo from '@/components/FrappeAnalyticsLogo.vue'

export default {
	name: 'App',
	components: {
		FrappeAnalyticsLogo,
		NotificationToasts,
	},
}
</script>
