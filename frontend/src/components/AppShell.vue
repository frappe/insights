<template>
	<div class="flex h-full w-full">
		<Sidebar v-if="!hideSidebar" />
		<div
			class="flex flex-1 flex-col p-6 pl-2"
			:class="[hideSidebar ? 'ml-4 w-full' : 'ml-[16rem] w-[calc(100%-16rem)]']"
		>
			<RouterView :key="$route.fullPath" />
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import settings from '@/utils/settings'
import { isOnboarded } from '@/utils/onboarding'
import Sidebar from '@/components/Sidebar.vue'

const hideSidebar = computed(() => {
	return settings.hide_sidebar || !isOnboarded.value
})
</script>
