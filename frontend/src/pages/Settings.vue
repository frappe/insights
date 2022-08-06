<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1">
				<h1 class="text-3xl font-medium text-gray-900">Settings</h1>
			</div>
		</template>
		<template #main>
			<div class="flex flex-1 flex-col space-y-6">
				<div class="space-y-3">
					<h2 class="text-xl">General</h2>
					<Input
						type="checkbox"
						label="Hide Sidebar"
						v-model="settings.hide_sidebar"
						@input="(checked) => settings.update('hide_sidebar', checked)"
					/>
				</div>
				<div class="space-y-3">
					<h2 class="text-xl">Queries</h2>
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
import useSettings from '@/utils/settings'

const settings = useSettings()

const pageMeta = ref({
	title: 'Settings',
})
updateDocumentTitle(pageMeta)
</script>
