<script setup lang="ts">
import { computed, inject } from 'vue'
import { Chart, getCachedChart } from '../charts/chart'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { WorkbookDashboardChart, WorkbookDashboardItem } from '../types/workbook.types'
import { Dashboard } from './dashboard'

const props = defineProps<{
	index: number
	item: WorkbookDashboardItem
}>()

const dashboard = inject('dashboard') as Dashboard

const chart = computed(() => {
	if (props.item.type != 'chart') return null
	const item = props.item as WorkbookDashboardChart
	return getCachedChart(item.chart) as Chart
})
</script>

<template>
	<div
		class="flex h-full w-full items-center rounded"
		:class="[
			dashboard.editing && dashboard.isActiveItem(index) ? 'outline outline-gray-700' : '',
		]"
		@click="dashboard.setActiveItem(index)"
	>
		<div class="h-full w-full" :class="dashboard.editing ? 'pointer-events-none' : ''">
			<ChartRenderer
				v-if="chart"
				:title="chart.doc.title"
				:chart_type="chart.doc.chart_type"
				:config="chart.doc.config"
				:operations="chart.doc.operations"
				:result="chart.dataQuery.result"
			/>
		</div>
	</div>
</template>
