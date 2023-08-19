<template>
	<div class="flex h-screen w-screen bg-white antialiased">
		<RouterView v-if="isGuestView" />
		<Suspense>
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

const route = useRoute()
const isGuestView = computed(() => route.meta.isGuestView)

if (!isGuestView.value) {
	const $socket = inject('$socket')
	const $notify = inject('$notify')
	const $auth = inject('$auth')
	$socket.on('insights_notification', (data) => {
		if (data.user == $auth.user.user_id) {
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
