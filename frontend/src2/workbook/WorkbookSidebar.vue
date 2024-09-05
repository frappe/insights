<script setup lang="ts">
import { LayoutPanelTop, Table2 } from 'lucide-vue-next'
import { inject } from 'vue'
import ChartIcon from '../charts/components/ChartIcon.vue'
import WorkbookSidebarListSection from './WorkbookSidebarListSection.vue'
import { Workbook, workbookKey } from './workbook'

const workbook = inject(workbookKey) as Workbook
</script>

<template>
	<div
		v-if="workbook"
		class="relative flex h-full w-[17rem] flex-shrink-0 flex-col overflow-y-auto bg-white shadow-sm"
	>
		<WorkbookSidebarListSection
			v-bind="{
				title: 'Queries',
				emptyMessage: 'No queries',
				items: workbook.doc.queries,
				itemKey: 'name',
				isActive: (idx: number) => workbook.isActiveTab('query', idx),
				add: workbook.addQuery,
				remove: (query) => workbook.removeQuery(query.name),
				route: (idx: number) => `/workbook/${workbook.name}/query/${idx}`,
			}"
		>
			<template #item-icon>
				<Table2 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</WorkbookSidebarListSection>

		<WorkbookSidebarListSection
			v-bind="{
				title: 'Charts',
				emptyMessage: 'No charts',
				items: workbook.doc.charts,
				itemKey: 'name',
				isActive: (idx: number) => workbook.isActiveTab('chart', idx),
				add: workbook.addChart,
				remove: (chart) => workbook.removeChart(chart.name),
				route: (idx: number) => `/workbook/${workbook.name}/chart/${idx}`,
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
				isActive: (idx: number) => workbook.isActiveTab('dashboard', idx),
				add: workbook.addDashboard,
				remove: (dashboard) => workbook.removeDashboard(dashboard.name),
				route: (idx: number) => `/workbook/${workbook.name}/dashboard/${idx}`,
			}"
		>
			<template #item-icon>
				<LayoutPanelTop class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</WorkbookSidebarListSection>
	</div>
</template>
