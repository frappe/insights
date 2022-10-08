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
})

const chartOptions = ref({
	title: props.title,
	tooltip: {
		trigger: 'item',
	},
	series: props.data.datasets.map((dataset) => {
		return {
			name: props.title,
			type: 'pie',
			radius: '65%',
			top: '-6%',
			data: dataset.data.map((value, index) => {
				return {
					name: props.data.labels[index],
					value: value,
				}
			}),
			labelLine: {
				show: false,
			},
			label: {
				show: false,
			},
			emphasis: {
				itemStyle: {
					shadowBlur: 5,
					shadowOffsetX: 0,
					shadowColor: 'rgba(0, 0, 0, 0.1)',
				},
			},
		}
	}),
})

// const chartOptions = ref({
// 	title: props.title,
// 	subtitle: props.subtitle,
// 	labels: props.data.labels,
// 	data: props.data.datasets.map((dataset) => {
// 		return {
// 			name: dataset.label,
// 			data: dataset.data,
// 			type: 'bar',
// 			itemStyle: {
// 				barBorderRadius: [4, 4, 0, 0],
// 			},
// 		}
// 	}),
// })
</script>

<template>
	<EChart :chartOptions="chartOptions" />
</template>
