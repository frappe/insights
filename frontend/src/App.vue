<template>
	<div class="flex h-screen select-none flex-col bg-gray-50 font-sans">
		<Topbar class="h-[3.5rem]" />
		<router-view
			class="mx-auto flex h-[calc(100%-3.5rem)] w-full max-w-[85rem] flex-col px-4 py-3 sm:px-6 lg:px-8"
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
