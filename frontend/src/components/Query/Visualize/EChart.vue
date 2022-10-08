<script setup>
import { onMounted, ref, onBeforeUnmount } from 'vue'
import { getColors } from '@/utils/charts/colors'
import * as echarts from 'echarts'

const props = defineProps({
	chartOptions: {
		type: Object,
		default: {},
	},
})

// cannot be overwritten
const defaultOptions = {
	fontFamily: 'Inter',
	grid: {
		top: props.chartOptions.subtitle ? 80 : 50,
		bottom: props.chartOptions.subtitle ? 80 : 60,
		left: 50,
		right: 50,
	},
	title: {
		text: props.chartOptions.title,
		subtext: props.chartOptions.subtitle,
		textStyle: {
			fontSize: 15,
			fontWeight: 500,
		},
		subtextStyle: {
			fontSize: 12,
			fontWeight: 400,
		},
	},
}

const customizableOptions = {
	color: getColors(),
	tooltip: {
		trigger: 'axis',
	},
	legend: {
		type: 'plain',
		bottom: 'bottom',
	},
}

let chart = null
const options = Object.assign({}, customizableOptions, props.chartOptions, defaultOptions)

const chartRef = ref(null)
onMounted(() => {
	chart = echarts.init(chartRef.value, 'light', {
		renderer: 'svg',
	})
	chart.setOption(options)
})

const resizeObserver = new ResizeObserver(() => {
	chart.resize()
})
onMounted(() => {
	setTimeout(() => {
		resizeObserver.observe(chartRef.value)
	}, 1000)
})
onBeforeUnmount(() => {
	resizeObserver.unobserve(chartRef.value)
})
</script>

<template>
	<div ref="chartRef" class="h-full w-full"></div>
</template>
