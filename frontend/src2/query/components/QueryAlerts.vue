<script setup lang="ts">
import { ref } from 'vue'
import { Query } from '../query'
import AlertSetupDialog from './AlertSetupDialog.vue'
import QueryAlertsDialog from './QueryAlertsDialog.vue'

// The alerts affordance, out of the table and into the callers that offer it.
// Setting up an alert is authoring, and its two dialogs are 42 kB of editor —
// which every surface that shows a result table used to carry, the viewer's
// included. The menu item that opens it is the caller's, so nothing here draws
// a control of its own.
defineProps<{ query: Query }>()

const show = defineModel<boolean>({ default: false })

const currentAlertName = ref('')
</script>

<template>
	<QueryAlertsDialog
		v-if="show"
		v-model="show"
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
