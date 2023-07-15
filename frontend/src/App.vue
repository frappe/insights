<template>
	<div class="flex h-screen w-screen bg-white font-sans antialiased">
		<template v-if="route.meta.allowGuest">
			<router-view></router-view>
		</template>
		<template v-else>
			<AppShell />
			<Toasts />
			<Dialog v-model="prompt.show" :options="prompt.options" />
		</template>
	</div>
</template>

<script setup>
import AppShell from '@/components/AppShell.vue'
import usePrompt from '@/utils/prompt'
import Toasts from '@/utils/toasts'
import { inject, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const prompt = usePrompt()

if (!route.meta.allowGuest) {
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
