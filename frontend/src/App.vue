<template>
	<div class="h-screen min-h-[44rem] min-w-[80rem] select-none bg-gray-50 font-sans">
		<RouterView :key="$route.fullPath" />
		<Toasts />
	</div>
</template>

<script setup>
import Toasts from '@/utils/toasts'

import { provide } from 'vue'
import { createToast } from '@/utils/toasts'
import $utils from '@/utils'

provide('$notify', createToast)
provide('$utils', $utils)
</script>
