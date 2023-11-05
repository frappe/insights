<script setup>
import widgets from '@/widgets/widgets'
import { computed, inject, ref } from 'vue'
import ChartSectionEmpty from './ChartSectionEmpty.vue'

const query = inject('query')
const builder = inject('builder')
const chartRefreshKey = ref(0)

const emptyMessage = computed(() => {
	if (query.doc.status == 'Pending Execution') {
		return 'Execute the query to see the chart'
	}
	if (!query.formattedResults?.length) {
		return 'No results found'
	}
	return 'Pick a chart type to get started'
})
</script>

<template>
	<div class="flex flex-1 items-center justify-center overflow-hidden rounded border">
		<div
			v-if="
				!builder.chart.doc?.name ||
				!query.formattedResults?.length ||
				query.doc.status == 'Pending Execution'
			"
			class="flex flex-1 flex-col items-center justify-center"
		>
			<ChartSectionEmpty></ChartSectionEmpty>
			<span class="text-gray-500">{{ emptyMessage }}</span>
		</div>
		<div v-else class="flex h-full w-full flex-1">
			<component
				v-if="builder.chart.doc.chart_type"
				ref="widget"
				:key="JSON.stringify(builder.chart.doc)"
				:is="widgets.getComponent(builder.chart.doc.chart_type)"
				:data="builder.chart.data"
				:options="builder.chart.doc.options"
			/>
		</div>
	</div>
</template>
