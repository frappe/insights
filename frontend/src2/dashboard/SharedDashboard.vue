<script setup lang="ts">
import { call } from 'frappe-ui'
import { ref } from 'vue'
import SharedChart from '../charts/SharedChart.vue'
import { WorkbookDashboard } from '../types/workbook.types'
import VueGridLayout from './VueGridLayout.vue'

const props = defineProps<{ dashboard_name: string }>()

const dashboard = ref<WorkbookDashboard>()

dashboard.value = await call('insights.api.dashboards.fetch_workbook_dashboard', {
	dashboard_name: props.dashboard_name,
})
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden">
		<div class="flex-1 overflow-y-auto p-4">
			<VueGridLayout
				v-if="dashboard && dashboard.items.length > 0"
				class="h-fit w-full"
				:cols="20"
				:disabled="true"
				:modelValue="dashboard.items.map((item) => item.layout)"
			>
				<template #item="{ index }">
					<div class="relative h-full w-full rounded p-2">
						<SharedChart :chart_name="dashboard.items[index].chart" />
					</div>
				</template>
			</VueGridLayout>
		</div>
	</div>
</template>
