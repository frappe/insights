<template>
	<div class="flex h-screen w-screen overflow-hidden bg-white text-base antialiased">
		<RouterView :key="$route.fullPath" />
		<Toaster :visible-toasts="2" position="bottom-right" />
		<component v-for="dialog in dialogs" :is="dialog" :key="dialog.id" />
	</div>
</template>

<script setup>
import { dialogs } from './helpers/confirm_dialog'
import { inject, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { Toaster } from 'vue-sonner'
import session from './session'

const route = useRoute()

if (!route.meta.isGuestView) {
	const $socket = inject('$socket')
	const $notify = inject('$notify')
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
