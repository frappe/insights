<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getFunnelChartOptions from './getFunnelChartOptions'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const labels = computed(() => {
	if (!props.data?.length || !props.options.xAxis) return []
	return props.data.map((d) => d[props.options.xAxis])
})
const dataset = computed(() => {
	if (!props.data?.length || !props.options.yAxis) return {}
	return {
		label: props.options.yAxis,
		data: props.data.map((d) => d[props.options.yAxis]),
	}
})

const funnelChartOptions = computed(() => {
	return getFunnelChartOptions(labels.value, dataset.value, props.options)
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="funnelChartOptions" />
</template>
