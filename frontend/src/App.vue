<template>
	<div class="flex h-screen w-screen bg-white antialiased">
		<RouterView v-if="isGuestView" />
		<Suspense v-else>
			<AppShell />
		</Suspense>
		<Toasts />
	</div>
</template>

<script setup>
import AppShell from '@/components/AppShell.vue'
import Toasts from '@/utils/toasts'
import { inject, onBeforeUnmount, computed } from 'vue'
import { useRoute } from 'vue-router'
import sessionStore from '@/stores/sessionStore'

const route = useRoute()
const isGuestView = computed(() => route.meta.isGuestView)

if (!isGuestView.value) {
	const $socket = inject('$socket')
	const $notify = inject('$notify')
	const session = sessionStore()
	$socket.on('insights_notification', (data) => {
		if (data.user == session.user.user_id) {
			$notify({
				title: data.title || data.message,
				message: data.title ? data.message : '',
				variant: data.type,
			})
		}
	})
	onBeforeUnmount(() => {
		$socket.off('insights_notification')
	})
}
</script>
