<template>
	<div class="flex flex-1 overflow-hidden bg-gray-50 text-base">
		<Sidebar v-if="!hideSidebar" />
		<div class="flex flex-1 flex-col overflow-hidden">
			<RouterView v-slot="{ Component }">
				<Suspense>
					<component :is="Component" :key="$route.fullPath" />
				</Suspense>
			</RouterView>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import auth from '@/utils/auth'
import Sidebar from '@/components/Sidebar.vue'
import { useRoute } from 'vue-router'
import settings from '@/utils/settings'

const route = useRoute()
const hideSidebar = computed(() => {
	return route.meta.hideSidebar || !auth.isLoggedIn
})
onMounted(() => auth.isLoggedIn && settings.get.fetch())
</script>
