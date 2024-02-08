<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getAxisChartOptions from '../AxisChart/getAxisChartOptions'
import getMixedAxisChartOptions from './getMixedAxisChartOptions'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const mixedAxisChartOptions = computed(() => {
	return getAxisChartOptions({
		chartType: undefined,
		options: props.options,
		data: props.data,
	})
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="mixedAxisChartOptions" />
</template>
