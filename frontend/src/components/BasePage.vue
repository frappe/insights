<template>
	<div class="flex flex-1 flex-col overflow-hidden bg-white p-5">
		<Breadcrumbs v-if="routes.length > 1" :routes="routes" />
		<header class="flex h-10 flex-shrink-0 overflow-visible">
			<slot name="header" />
		</header>
		<main class="flex flex-1 overflow-hidden">
			<slot name="main" />
		</main>
	</div>
</template>

<script setup>
import Breadcrumbs from '@/components/Breadcrumbs.vue'

import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const routes = computed(() => {
	return route.path
		.split('/')
		.filter(Boolean)
		.reduce((routes, path) => {
			routes.push({
				name: decodeURIComponent(path)
					.split('-')
					.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
					.join(' '),
				path: routes.length ? `${routes[routes.length - 1].path}/${path}` : `${path}`,
			})
			return routes
		}, [])
})
</script>
