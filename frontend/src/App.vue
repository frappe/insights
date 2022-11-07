<template>
	<div class="h-screen min-h-[44rem] min-w-[80rem] bg-gray-50 font-sans">
		<CommandPalette />
		<AppShell />
		<Toasts />
	</div>
</template>

<script setup>
import Toasts from '@/utils/toasts'
import AppShell from '@/components/AppShell.vue'
import CommandPalette from '@/components/CommandPalette.vue'
import { inject, onBeforeUnmount } from 'vue'

const $socket = inject('$socket')
const $notify = inject('$notify')
const $auth = inject('$auth')
$socket.on('insights_notification', (data) => {
	if (data.user == $auth.user.user_id) {
		$notify({
			title: data.title || data.message,
			message: data.title ? data.message : '',
			appearance: data.type,
		})
	}
})
onBeforeUnmount(() => {
	$socket.off('insights_notification')
})
</script>
