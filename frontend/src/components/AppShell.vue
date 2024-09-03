<template>
	<div class="flex flex-1 overflow-hidden text-base">
		<Sidebar v-if="!hideSidebar" />
		<RouterView v-slot="{ Component }">
			<Suspense>
				<div class="flex flex-1 flex-col overflow-hidden">
					<component :is="Component" :key="$route.fullPath" />
				</div>
				<template #fallback>
					<SuspenseFallback />
				</template>
			</Suspense>
		</RouterView>
	</div>
</template>

<script setup>
import Sidebar from '@/components/Sidebar.vue'
import SuspenseFallback from '@/components/SuspenseFallback'
import sessionStore from '@/stores/sessionStore'
import settingsStore from '@/stores/settingsStore'
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

const session = sessionStore()
const route = useRoute()
const hideSidebar = ref(true)
watch(
	route,
	(newRoute) => {
		hideSidebar.value = newRoute.meta.hideSidebar || !session.isLoggedIn
	},
	{ immediate: true }
)
onMounted(() => session.isLoggedIn && settingsStore())
</script>
