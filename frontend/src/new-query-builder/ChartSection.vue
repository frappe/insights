<script setup>
import widgets from '@/widgets/widgets'
import { computed, inject, ref, watch } from 'vue'
import ChartSectionEmpty from './ChartSectionEmpty.vue'

const query = inject('query')
const builder = inject('builder')
const chartRefreshKey = ref(0)

watch(
	() => builder.chart.chartDoc,
	() => (chartRefreshKey.value += 1),
	{ deep: true }
)

const emptyMessage = computed(() => {
	if (query.doc.status == 'Pending Execution') {
		return 'Execute the query to see the chart'
	}
	if (!query.doc.results?.length) {
		return 'No results found'
	}
	return 'Pick a chart type to get started'
})
</script>

<template>
	<div class="flex flex-1 items-center justify-center overflow-hidden rounded border">
		<div
			v-if="
				!builder.chart.chartDoc?.name ||
				!query.doc.results?.length ||
				query.doc.status == 'Pending Execution'
			"
			class="flex flex-1 flex-col items-center justify-center"
		>
			<ChartSectionEmpty></ChartSectionEmpty>
			<span class="text-gray-500">{{ emptyMessage }}</span>
		</div>
		<div v-else class="flex h-full w-full flex-1">
			<component
				v-if="builder.chart.chartDoc.chart_type"
				:key="chartRefreshKey"
				ref="widget"
				:is="widgets.getComponent(builder.chart.chartDoc.chart_type)"
				:data="builder.chart.chartData"
				:options="builder.chart.chartDoc.options"
			/>
		</div>
	</div>
</template>
