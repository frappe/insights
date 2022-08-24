<template>
	<div
		class="flex h-[calc(100%)] min-h-[38rem] flex-col rounded-md border bg-white px-5 py-4 shadow-md"
	>
		<!-- 1.5rem -->
		<Breadcrumbs v-if="routes.length > 1" :routes="routes" />
		<header class="flex h-10 flex-shrink-0">
			<slot name="header" />
		</header>
		<main
			class="flex"
			:class="[routes.length > 1 ? 'h-[calc(100%-4.25rem)]' : 'h-[calc(100%-2.5rem)]']"
		>
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
