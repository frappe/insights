<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getScatterChartOptions from './getScatterChartOptions'
import getAxisChartOptions from '../AxisChart/getAxisChartOptions'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const scatterChartOptions = computed(() => {
	return getAxisChartOptions({
		chartType: 'scatter',
		options: props.options,
		data: props.data,
	})
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="scatterChartOptions" />
</template>
