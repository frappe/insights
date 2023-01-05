<template>
	<div class="flex flex-1 overflow-hidden text-base">
		<Sidebar v-if="!hideSidebar" />
		<div class="flex flex-1 flex-col overflow-hidden">
			<RouterView :key="$route.fullPath" />
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import auth from '@/utils/auth'
import { setupComplete } from '@/utils/setupWizard'
import Sidebar from '@/components/Sidebar.vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const hideSidebar = computed(() => {
	return route.meta.hideSidebar || !setupComplete.value || !auth.isLoggedIn
})
</script>
