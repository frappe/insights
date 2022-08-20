<script setup>
import { getRandomColor } from '@/utils/visualizations'
import { onMounted, ref } from 'vue'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)
Chart.defaults.font.family = 'Inter'
Chart.defaults.font.style = 'inherit'

const chartOptions = {
	responsive: true,
	maintainAspectRatio: false,
	plugins: {
		legend: {
			position: 'bottom',
		},
	},
	scales: {
		x: {
			grid: {
				display: false,
			},
		},
		y: {
			grid: {
				display: false,
			},
		},
	},
}

const props = defineProps({
	data: {
		type: Object,
		required: true,
	},
	options: {
		type: Object,
		default: {},
	},
})
const chartData = {
	labels: props.data.labels,
	datasets: props.data.datasets.map((dataset) => {
		const color = getRandomColor(2)
		return {
			data: dataset.data,
			label: dataset.label,
			backgroundColor: color[0],
			borderColor: color[1],
			pointRadius: 0,
			borderWidth: 2,
			tension: props.options.tension,
		}
	}),
}

const chartRef = ref(null)
onMounted(() => {
	new Chart(chartRef.value, {
		type: 'line',
		data: chartData,
		options: chartOptions,
	})
})
</script>

<template>
	<div class="flex h-full w-full justify-center pt-2">
		<canvas ref="chartRef"></canvas>
	</div>
</template>
