<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getAxisChartOptions from '../AxisChart/getAxisChartOptions'
import getLineChartOptions from './getLineChartOptions'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const lineChartOptions = computed(() => {
	return getAxisChartOptions({
		chartType: 'line',
		options: props.options,
		data: props.data,
	})
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="lineChartOptions" />
</template>
