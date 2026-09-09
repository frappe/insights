<script setup lang="ts">
import { provide } from 'vue'
import useDashboard from './dashboard'
import DashboardItem from './DashboardItem.vue'
import StaticGridLayout from './StaticGridLayout.vue'
import { call } from 'frappe-ui'

const props = defineProps<{ dashboard_name: string }>()

const dashboard_name = await call('insights.api.shared.get_dashboard_name', {
	dashboard_name: props.dashboard_name,
})

const dashboard = useDashboard(dashboard_name)
// whoever follows the link reads the saved charts, not the config being edited
dashboard.shared = true
provide('dashboard', dashboard)
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden">
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
