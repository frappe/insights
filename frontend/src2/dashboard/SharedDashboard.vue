<script setup lang="ts">
import { provide } from 'vue'
import useDashboard from './dashboard'
import DashboardItem from './DashboardItem.vue'
import StaticGridLayout from './StaticGridLayout.vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'

const props = defineProps<{ dashboard_name: string }>()

const dashboard = useDashboard(props.dashboard_name)
// whoever follows the link reads the saved charts, not the config being edited
dashboard.shared = true
provide('dashboard', dashboard)
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden">
		<LoadingOverlay v-if="dashboard.pending" />
		<div class="flex-1 overflow-y-auto p-4">
			<StaticGridLayout
				v-if="dashboard.doc.items.length > 0"
				class="h-fit w-full"
				:items="dashboard.doc.items"
				:rules="dashboard.cellRules"
			>
				<template #item="{ index }">
					<DashboardItem :index="index" :item="dashboard.doc.items[index]" />
				</template>
			</StaticGridLayout>
		</div>
	</div>
</template>
