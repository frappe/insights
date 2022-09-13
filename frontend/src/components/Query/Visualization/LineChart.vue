<script setup>
import { getColors } from '@/utils/visualizations/colors'
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
				display: true,
			},
		},
	},
}

const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	data: {
		type: Object,
		required: true,
	},
	options: {
		type: Object,
		default: {},
	},
})
const colors = getColors(props.data.datasets.length)
const chartData = {
	labels: props.data.labels,
	datasets: props.data.datasets.map((dataset, i) => {
		return {
			data: dataset.data,
			label: dataset.label,
			backgroundColor: colors[i],
			borderColor: colors[i],
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
	<div class="h-full w-full">
		<div class="h-5 text-base font-semibold text-gray-600">{{ props.title }}</div>
		<div class="flex h-[calc(100%-1.5rem)] w-full justify-center pt-2">
			<canvas ref="chartRef"></canvas>
		</div>
	</div>
</template>
