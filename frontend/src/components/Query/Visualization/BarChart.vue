<script setup>
import { getRandomColor } from '@/utils/visualization'
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
}

const props = defineProps({
	data: {
		type: Object,
		required: true,
	},
})
const chartData = {
	labels: props.data.labels,
	datasets: props.data.datasets.map((dataset) => ({
		data: dataset.data,
		label: dataset.label,
		backgroundColor: getRandomColor(),
		barPercentage: 0.7,
		borderRadius: 4,
	})),
}

const chartRef = ref(null)
onMounted(() => {
	new Chart(chartRef.value, {
		type: 'bar',
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
