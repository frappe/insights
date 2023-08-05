<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getScatterChartOptions from './getScatterChartOptions'

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
	return props.options.yAxis.map((column) => {
		return {
			label: column,
			data: props.data.map((d) => d[column]),
		}
	})
})

const scatterChartOptions = computed(() => {
	return getScatterChartOptions(labels.value, datasets.value, props.options)
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="scatterChartOptions" />
</template>
