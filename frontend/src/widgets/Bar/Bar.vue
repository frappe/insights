<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getAxisChartOptions from '../AxisChart/getAxisChartOptions'
import getBarChartOptions from './getBarChartOptions'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const barChartOptions = computed(() => {
	return getAxisChartOptions({
		chartType: 'bar',
		options: props.options,
		data: props.data,
	})
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="barChartOptions" />
</template>
