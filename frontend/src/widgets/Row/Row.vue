<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getAxisChartOptions from '../AxisChart/getAxisChartOptions'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const rowChartOptions = computed(() => {
	const barChartOptions = getAxisChartOptions({
		chartType: 'bar',
		options: props.options,
		data: props.data,
	})

	if (!barChartOptions.xAxis || !barChartOptions.yAxis) {
		return barChartOptions
	}

	const yAxis = barChartOptions.yAxis || {}
	const xAxis = barChartOptions.xAxis || {}
	xAxis.data = xAxis.data?.reverse()
	const datasets = barChartOptions.series.map((dataset) => {
		dataset.data = dataset.data.reverse()
		dataset.itemStyle.borderRadius = [0, 4, 4, 0]
		return dataset
	})

	return {
		...barChartOptions,
		xAxis: yAxis,
		yAxis: xAxis,
		series: datasets,
	}
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="rowChartOptions" />
</template>
