<template>
	<div class="flex h-screen select-none font-sans text-gray-800">
		<div class="flex h-full flex-1 flex-col">
			<Topbar />
			<router-view class="flex h-[calc(100vh-4rem)] flex-col" />
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
