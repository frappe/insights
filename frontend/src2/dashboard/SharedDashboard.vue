<script setup lang="ts">
import { provide } from 'vue'
import useDashboard from './dashboard'
import DashboardItem from './DashboardItem.vue'
import VueGridLayout from './VueGridLayout.vue'
import { call } from 'frappe-ui'

const props = defineProps<{ dashboard_name: string }>()

const dashboard_name = await call('insights.api.shared.get_dashboard_name', {
	dashboard_name: props.dashboard_name,
})

const dashboard = useDashboard(dashboard_name)
provide('dashboard', dashboard)
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden">
		<div class="flex-1 overflow-y-auto p-4">
			<VueGridLayout
				v-if="dashboard.doc.items.length > 0"
				class="h-fit w-full"
				:cols="20"
				:disabled="true"
				:modelValue="dashboard.doc.items.map((item) => item.layout)"
			>
				<template #item="{ index }">
					<DashboardItem :index="index" :item="dashboard.doc.items[index]" />
				</template>
			</VueGridLayout>
		</div>
	</div>
</template>
