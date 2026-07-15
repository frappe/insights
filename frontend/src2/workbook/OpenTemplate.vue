<script setup lang="ts">
import { call, LoadingIndicator } from 'frappe-ui'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createToast } from '../helpers/toasts'
import { __ } from '../translation'

// Resolves a shipped workbook template to its dashboard, lazily importing it on
// first open (idempotent server-side). Entry point for the ERPNext workspace
// nudge, so the desk banner links to a stable template id instead of a docname.
const props = defineProps<{ app: string; folder: string }>()
const router = useRouter()

onMounted(() => {
	call('insights.api.templates.create_workbook_from_template', {
		template_name: `${props.app}/${props.folder}`,
	})
		.then((result: { workbook: number; dashboard: string | null }) => {
			router.replace(
				result.dashboard
					? `/dashboards/${result.dashboard}`
					: `/workbook/${result.workbook}`,
			)
		})
		.catch(() => {
			createToast({ message: __('Could not open the dashboard'), variant: 'error' })
			router.replace('/workbook')
		})
})
</script>

<template>
	<div class="flex h-full w-full flex-col items-center justify-center gap-2 text-ink-gray-5">
		<LoadingIndicator class="w-7" />
		<p class="text-sm">{{ __('Preparing dashboard…') }}</p>
	</div>
</template>
