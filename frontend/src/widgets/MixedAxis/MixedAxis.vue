<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getMixedAxisChartOptions from './getMixedAxisChartOptions'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const labels = computed(() => {
	if (!props.data?.length || !props.options.xAxis) return []
	return props.data.map((d) => d[props.options.xAxis])
})

const datasets = computed(() => {
	if (!props.data?.length || !props.options.yAxis) return []
	return (
		props.options.yAxis
			// to exclude the columns that might be removed from the query but not the chart
			.filter((series) => props.data[0].hasOwnProperty(series.column))
			.map((series) => {
				const column = series.column || series
				return {
					label: column,
					data: props.data.map((d) => d[column]),
					options: series,
				}
			})
	)
})

const mixedAxisChartOptions = computed(() => {
	return getMixedAxisChartOptions(labels.value, datasets.value, props.options)
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="mixedAxisChartOptions" />
</template>
