<template>
	<div class="flex h-screen select-none font-sans text-gray-800">
		<Sidebar />

		<div class="flex flex-1 flex-col pl-64">
			<Topbar />

			<router-view class="flex flex-1 flex-col" />
		</div>

		<NotificationToasts />
	</div>
</template>

<script>
import { NotificationToasts } from 'frappe-ui'
import Sidebar from '@/components/Sidebar.vue'
import Topbar from '@/components/Topbar.vue'

export default {
	name: 'App',
	components: {
		Sidebar,
		Topbar,
		NotificationToasts,
	},
}
</script>
