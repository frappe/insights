<script setup lang="ts">
import { call } from 'frappe-ui'
import { computed, ref } from 'vue'
import SharedChart from '../charts/SharedChart.vue'
import { WorkbookDashboard } from '../types/workbook.types'
import DashboardText from './DashboardText.vue'
import SharedDashboardFilter from './SharedDashboardFilter.vue'
import VueGridLayout from './VueGridLayout.vue'

const props = defineProps<{ dashboard_name: string }>()

const dashboard = ref<WorkbookDashboard>()

dashboard.value = await call('insights.api.dashboards.fetch_workbook_dashboard', {
	dashboard_name: props.dashboard_name,
})

const items = computed(() => dashboard.value?.items || [])
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden">
		<div class="flex-1 overflow-y-auto p-4">
			<VueGridLayout
				v-if="dashboard && items.length > 0"
				class="h-fit w-full"
				:cols="20"
				:disabled="true"
				:modelValue="dashboard.items.map((item) => item.layout)"
			>
				<template #item="{ index }">
					<div class="relative h-full w-full rounded p-2">
						<SharedChart
							v-if="items[index].type == 'chart'"
							:chart_name="items[index].chart"
						/>

						<DashboardText
							v-else-if="items[index].type === 'text'"
							:item="items[index]"
						/>

						<SharedDashboardFilter
							v-else-if="items[index].type === 'filter'"
							:item="items[index]"
						/>
					</div>
				</template>
			</VueGridLayout>
		</div>
	</div>
</template>
