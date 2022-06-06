<template>
	<div class="flex h-screen select-none flex-col bg-white font-sans">
		<Topbar />
		<router-view
			class="mx-auto flex h-[calc(100%-4rem)] w-full max-w-[85rem] flex-col px-4 sm:px-6 lg:px-8"
			:key="$route.fullPath"
		/>
		<Toasts />
	</div>
</template>

<script>
import { Toasts } from '@/utils/toasts'
import Topbar from '@/components/Topbar.vue'

export default {
	name: 'App',
	components: {
		Topbar,
		Toasts,
	},
}
</script>
