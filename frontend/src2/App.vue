<template>
	<div class="flex h-screen w-screen overflow-hidden bg-surface-base text-base antialiased">
		<div v-if="!hideSidebar" class="h-full border-r bg-surface-gray-1">
			<AppSidebar />
		</div>

		<div class="flex h-full flex-1 flex-col overflow-auto">
			<RouterView />
		</div>

		<template>
			<component v-for="dialog in dialogs" :is="dialog" :key="dialog.id" />
		</template>

		<ToastProvider />
	</div>
</template>

<script setup lang="ts">
import { ToastProvider, toast } from 'frappe-ui'
import { computed, ref, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import { dialogs } from './helpers/confirm_dialog'
import { attachRealtimeListener } from './helpers/index.ts'
import session from './session'

const route = useRoute()
const hideSidebar = ref(true)
watchEffect(() => {
	if (route.fullPath === '/') return
	hideSidebar.value = Boolean(route.meta.isGuestView || route.meta.hideSidebar)
})

const isGuestView = computed(() => route.meta.isGuestView || !session.isLoggedIn)

const notifiers = {
	success: toast.success,
	error: toast.error,
	warning: toast.warning,
	info: toast.info,
}

attachRealtimeListener('insights_notification', (data: any) => {
	if (data.user == session.user.email) {
		const notify = notifiers[data.type as keyof typeof notifiers] || toast.message
		notify(data.title || data.message, {
			description: data.title ? data.message : undefined,
			duration: data.duration ? data.duration * 1000 : undefined,
		})
	}
})
</script>
