<script setup>
import { inject } from 'vue'
import DashboardMenuButton from './DashboardMenuButton.vue'
import DashboardShareButton from './DashboardShareButton.vue'
const dashboard = inject('dashboard')
</script>

<template>
	<div class="flex flex-shrink-0 justify-end space-x-2">
		<DashboardMenuButton />
		<DashboardShareButton v-if="!dashboard.editing && dashboard.canShare" />
		<Button
			v-else-if="dashboard.editing"
			appearance="white"
			class="border-red-500 text-red-500"
			@click="dashboard.discardChanges"
		>
			Discard
		</Button>

		<Button
			v-if="!dashboard.editing"
			appearance="white"
			class="border-blue-600 !font-medium text-blue-600"
			@click="dashboard.edit"
		>
			Edit
		</Button>
		<Button v-else appearance="primary" @click="dashboard.save"> Save </Button>
	</div>
</template>
