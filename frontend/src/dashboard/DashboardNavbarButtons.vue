<script setup>
import { useMagicKeys, whenever } from '@vueuse/core'
import { inject } from 'vue'
import DashboardMenuButton from './DashboardMenuButton.vue'
import DashboardShareButton from './DashboardShareButton.vue'
const dashboard = inject('dashboard')

const keys = useMagicKeys()
const cmdE = keys['Meta+E']
whenever(cmdE, dashboard.edit)
const cmdS = keys['Meta+S']
whenever(cmdS, dashboard.save)
const cmdD = keys['Meta+D']
whenever(cmdD, dashboard.discardChanges)
</script>

<template>
	<div class="flex flex-shrink-0 justify-end space-x-2">
		<DashboardShareButton v-if="!dashboard.editing && dashboard.canShare" />
		<Button variant="outline" v-if="!dashboard.editing" @click="dashboard.refresh">
			Refresh
		</Button>
		<Button v-if="dashboard.editing" variant="outline" @click="dashboard.discardChanges">
			Cancel
		</Button>
		<Button v-if="!dashboard.editing" variant="outline" @click="dashboard.edit"> Edit </Button>
		<Button v-else variant="solid" @click="dashboard.save" :loading="dashboard.loading">
			Save
		</Button>
		<DashboardMenuButton />
	</div>
</template>
