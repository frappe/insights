<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1">
				<h1 class="text-3xl font-medium text-gray-900">Settings</h1>
			</div>
		</template>
		<template #main>
			<div class="flex w-2/3 flex-col space-y-6">
				<div class="space-y-3">
					<div class="text-sm tracking-wide text-gray-600">GENERAL</div>
					<Input
						type="checkbox"
						label="Hide Sidebar"
						v-model="settings.hide_sidebar"
						@input="(checked) => settings.update('hide_sidebar', checked)"
					/>
				</div>
				<div class="space-y-3">
					<div class="text-sm tracking-wide text-gray-600">QUERY</div>
					<Button appearance="white" @click="$router.push('/settings/running-queries')">
						Show Running Queries
					</Button>
				</div>
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import { ref } from 'vue'
import BasePage from '@/components/BasePage.vue'
import { updateDocumentTitle } from '@/utils'
import settings from '@/utils/settings'

const pageMeta = ref({
	title: 'Settings',
})
updateDocumentTitle(pageMeta)
</script>
