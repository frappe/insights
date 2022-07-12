<template>
	<div class="h-screen min-h-[42rem] min-w-[80rem] select-none bg-gray-50 font-sans">
		<RouterView :key="$route.fullPath" />
		<Toasts />
	</div>
</template>

<script setup>
import Toasts from '@/utils/toasts'
// import NavBar from '@/components/NavBar.vue'

import { provide } from 'vue'
import { createToast } from '@/utils/toasts'
// import { isOnboarded } from '@/controllers/onboarding'

provide('$notify', createToast)
</script>
