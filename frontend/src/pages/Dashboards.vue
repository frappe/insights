<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1">
				<h1 class="text-3xl font-medium text-gray-900">Dashboards</h1>
			</div>
		</template>
		<template #main>
			<div class="h-96 w-full rounded-lg border-4 border-dashed border-gray-200"></div>
		</template>
	</BasePage>
</template>

<script setup>
import { ref } from 'vue'
import BasePage from '@/components/BasePage.vue'
import { updateDocumentTitle } from '@/utils/document'

const pageMeta = ref({
	title: 'Dashboards',
})
updateDocumentTitle(pageMeta)
</script>
