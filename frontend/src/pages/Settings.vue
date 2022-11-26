<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1">
				<h1 class="text-3xl font-medium text-gray-900">Settings</h1>
			</div>
		</template>
		<template #main>
			<div class="flex w-1/3 flex-col space-y-6" v-if="settings.doc">
				<div class="space-y-4">
					<div class="text-sm tracking-wide text-gray-600">GENERAL</div>
					<Input
						type="checkbox"
						label="Auto Execute Query"
						:value="settings.doc.auto_execute_query"
						@input="(c) => settings.updateSettings({ auto_execute_query: c })"
					/>
					<Input
						type="number"
						min="0"
						label="Auto Refresh Dashboard In (Minutes)"
						:value="settings.doc.auto_refresh_dashboard_in_minutes"
						@input="
							(c) => settings.updateSettings({ auto_refresh_dashboard_in_minutes: c })
						"
					/>
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
