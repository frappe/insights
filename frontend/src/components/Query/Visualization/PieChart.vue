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
		hoverOffset: 4,
		data: dataset.data,
		label: dataset.label,
		backgroundColor: getRandomColor(dataset.data.length),
	})),
}

const chartRef = ref(null)
onMounted(() => {
	new Chart(chartRef.value, {
		type: 'pie',
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
