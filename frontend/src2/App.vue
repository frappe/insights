<template>
	<div
		class="flex w-screen bg-surface-base text-base antialiased"
		:class="capture ? 'min-h-screen' : 'h-screen overflow-hidden'"
	>
		<div v-if="!hideSidebar" class="h-full border-r bg-surface-gray-1 max-sm:hidden">
			<AppSidebar />
		</div>

		<div class="flex min-w-0 flex-1 flex-col" :class="capture ? '' : 'h-full'">
			<div class="flex min-h-0 flex-1 flex-col" :class="capture ? '' : 'overflow-auto'">
				<RouterView />
			</div>
			<MobileTabBar v-if="!hideSidebar && !capture" />
		</div>

		<template>
			<component v-for="dialog in dialogs" :is="dialog" :key="dialog.id" />
		</template>

		<UpgradeWizard v-if="session.isAuthorized && !isGuestView" />

		<ToastProvider />
	</div>
</template>

<script setup lang="ts">
import { ToastProvider, toast } from 'frappe-ui'
import { computed, ref, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import MobileTabBar from './components/MobileTabBar.vue'
import UpgradeWizard from './upgrade/UpgradeWizard.vue'
import { dialogs } from './helpers/confirm_dialog'
import { attachRealtimeListener } from './helpers/index.ts'
import session from './session'
import { isCapture } from './dashboard/capture'

const route = useRoute()
const hideSidebar = ref(true)
watchEffect(() => {
	if (route.fullPath === '/') return
	hideSidebar.value = Boolean(route.meta.isGuestView || route.meta.hideSidebar)
})

const isGuestView = computed(() => route.meta.isGuestView || !session.isLoggedIn)
// A page the server captures as an image lays out at its full height, so the
// capture holds all of it (`dashboard/capture.ts`)
const capture = computed(() => isCapture(route.query))

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
