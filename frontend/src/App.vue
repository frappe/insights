<template>
	<div class="flex h-screen select-none flex-col bg-gray-50 font-sans">
		<Topbar v-if="isOnboarded" class="h-[3.5rem]" />
		<router-view
			class="mx-auto flex w-full max-w-[85rem] flex-col px-4 py-3 sm:px-6 lg:px-8"
			:class="{ 'h-[calc(100%-3.5rem)]': isOnboarded, 'h-full': !isOnboarded }"
			:key="$route.fullPath"
		/>
		<Toasts />
	</div>
</template>

<script setup>
import Toasts from '@/utils/toasts'
import Topbar from '@/components/Topbar.vue'

import { provide } from 'vue'
import { createToast } from '@/utils/toasts'
import { isOnboarded } from '@/controllers/onboarding'

provide('$notify', createToast)
</script>
