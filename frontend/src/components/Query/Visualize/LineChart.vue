<script setup>
import { ref } from 'vue'
import EChart from './EChart.vue'

const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	data: {
		type: Object,
		default: {},
	},
	options: {
		type: Object,
		default: {},
	},
})

const chartOptions = ref({
	title: props.title,
	subtitle: props.subtitle,
	xAxis: {
		type: 'category',
		data: props.data.labels,
	},
	yAxis: {
		type: 'value',
	},
	series: props.data.datasets.map((dataset) => {
		return {
			name: dataset.label,
			data: dataset.data,
			type: 'line',
			smooth: props.options.smoothLines,
			showSymbol: props.options.showPoints,
		}
	}),
})
</script>

<template>
	<EChart :chartOptions="chartOptions" />
</template>
