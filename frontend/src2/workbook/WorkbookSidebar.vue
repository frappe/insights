<script setup lang="ts">
import { Braces, LayoutPanelTop, ScrollText, Table2 } from 'lucide-vue-next'
import { computed, inject } from 'vue'
import { useRoute } from 'vue-router'
import WorkbookSidebarListSection from './WorkbookSidebarListSection.vue'
import { workbookKey } from './workbook'
import ChartIcon from '../charts/components/ChartIcon.vue'

const workbook = inject(workbookKey)!
const route = useRoute()

const activeQueryName = computed(() => {
	if (route.name === 'WorkbookQuery') {
		const query_name = route.params.query_name as string
		return workbook.doc.queries.find((query) => query.name === query_name)?.name
	}
})
</script>

<template>
	<div
		v-if="workbook"
		class="relative z-[1] flex h-full w-[17rem] flex-shrink-0 flex-col overflow-y-auto bg-white"
	>
		<WorkbookSidebarListSection
			v-bind="{
				title: 'Queries',
				emptyMessage: 'No queries',
				items: workbook.doc.queries,
				itemKey: 'name',
				add: workbook.addQuery,
				remove: (query) => workbook.removeQuery(query.name),
				isActive: (query) => workbook.isActiveTab('query', query.name),
				route: (query) => `/workbook/${workbook.name}/query/${query.name}`,
			}"
		>
			<template #item-icon="{ item }">
				<ScrollText
					v-if="item.is_native_query"
					class="h-4 w-4 text-gray-700"
					stroke-width="1.5"
				/>
				<Braces
					v-else-if="item.is_script_query"
					class="h-4 w-4 text-gray-700"
					stroke-width="1.5"
				/>
				<Table2 v-else class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</WorkbookSidebarListSection>

		<WorkbookSidebarListSection
			v-bind="{
				title: 'Charts',
				emptyMessage: 'No charts',
				items: workbook.doc.charts,
				itemKey: 'name',
				add: () => workbook.addChart(activeQueryName),
				remove: (chart) => workbook.removeChart(chart.name),
				isActive: (chart) => workbook.isActiveTab('chart', chart.name),
				route: (chart) => `/workbook/${workbook.name}/chart/${chart.name}`,
			}"
		>
			<template #item-icon="{ item }">
				<ChartIcon :chart-type="item.chart_type" />
			</template>
		</WorkbookSidebarListSection>

		<WorkbookSidebarListSection
			v-bind="{
				title: 'Dashboards',
				emptyMessage: 'No dashboards',
				items: workbook.doc.dashboards,
				itemKey: 'name',
				add: workbook.addDashboard,
				remove: (dashboard) => workbook.removeDashboard(dashboard.name),
				isActive: (dashboard) => workbook.isActiveTab('dashboard', dashboard.name),
				route: (dashboard) => `/workbook/${workbook.name}/dashboard/${dashboard.name}`,
			}"
		>
			<template #item-icon>
				<LayoutPanelTop class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</WorkbookSidebarListSection>
	</div>
</template>
