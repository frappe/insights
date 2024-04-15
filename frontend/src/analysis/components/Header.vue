<script setup lang="ts">
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import { inject } from 'vue'
import { analysisKey } from '../useAnalysis'

const analysis = inject(analysisKey)
</script>

<template>
	<header
		class="sticky top-0 z-10 flex w-full flex-shrink-0 items-center justify-between border-b bg-white px-4 py-2.5"
	>
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Analysis', route: { path: '/analysis' } },
				{ label: analysis?.title, route: { path: '/analysis' } },
			]"
		/>
	</header>
</template>
