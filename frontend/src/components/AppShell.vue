<template>
	<div class="flex flex-1 overflow-hidden bg-gray-50 text-base">
		<Sidebar v-if="!hideSidebar" />
		<RouterView v-slot="{ Component }">
			<Suspense>
				<div class="flex flex-1 flex-col overflow-hidden">
					<component :is="Component" :key="$route.fullPath" />
				</div>
				<template #fallback>
					<div class="flex h-full flex-col items-center justify-center">
						<FeatherIcon name="loader" class="h-8 w-8 animate-spin text-gray-500" />
					</div>
				</template>
			</Suspense>
		</RouterView>
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
