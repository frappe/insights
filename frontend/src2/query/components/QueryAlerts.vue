<script setup lang="ts">
import { Button } from 'frappe-ui'
import { Bell } from 'lucide-vue-next'
import { ref } from 'vue'
import { Query } from '../query'
import AlertSetupDialog from './AlertSetupDialog.vue'
import QueryAlertsDialog from './QueryAlertsDialog.vue'

// The alerts affordance, out of the table and into the callers that offer it.
// Setting up an alert is authoring, and its two dialogs are 42 kB of editor —
// which every surface that shows a result table used to carry, the viewer's
// included.
defineProps<{ query: Query }>()

const showAlertsDialog = ref(false)
const currentAlertName = ref('')
</script>

<template>
	<Button variant="ghost" @click="showAlertsDialog = true">
		<template #icon>
			<Bell class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
		</template>
	</Button>

	<QueryAlertsDialog
		v-if="showAlertsDialog"
		v-model="showAlertsDialog"
		:query="query"
		@set-current-alert-name="currentAlertName = $event"
	>
	</QueryAlertsDialog>

	<AlertSetupDialog
		v-if="currentAlertName"
		:modelValue="Boolean(currentAlertName)"
		@update:model-value="!$event ? (currentAlertName = '') : undefined"
		:query="query"
		:alert_name="currentAlertName"
	/>
</template>
