<script setup>
import BaseChart from '@/components/Charts/BaseChart.vue'
import { computed } from 'vue'
import getLineChartOptions from './getLineChartOptions'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const xAxis = computed(() => {
	let xAxis = props.options.xAxis
	if (!xAxis) return []
	if (typeof xAxis === 'string') xAxis = [{ column: xAxis }]
	if (Array.isArray(xAxis) && xAxis.length) xAxis = xAxis.map(({ column }) => column)
	// remove the columns that might be removed from the query but not the chart
	xAxis = xAxis.filter((column) => props.data[0].hasOwnProperty(column))
	return xAxis
})

const labels = computed(() => {
	if (!props.data?.length) return []
	let firstAxis = xAxis.value[0]
	if (typeof firstAxis !== 'string') return console.warn('xAxis must be a string')

	const labels = props.data.map((d) => d[firstAxis])
	const uniqueLabels = [...new Set(labels)]
	return uniqueLabels
})

const datasets = computed(() => {
	let yAxis = props.options.yAxis
	if (!props.data?.length || !yAxis) return []
	if (typeof yAxis === 'string') yAxis = [yAxis]

	const validSeries = yAxis
		// to exclude the columns that might be removed from the query but not the chart
		.filter(
			(series) =>
				props.data[0].hasOwnProperty(series?.column) || props.data[0].hasOwnProperty(series)
		)

	if (xAxis.value.length == 1) {
		// even if data has multiple points for each yAxis series
		// for eg. Month Oct has 3 points for each Price, we need to combine them into one point by summing them up
		return validSeries.map((series) => {
			const column = series.column || series
			const seriesOptions = series.series_options || {}
			const data = labels.value.map((label) => {
				const points = props.data.filter((d) => d[xAxis.value[0]] === label)
				const sum = points.reduce((acc, curr) => acc + curr[column], 0)
				return sum
			})
			return {
				label: column,
				data,
				series_options: seriesOptions,
			}
		})
	}

	const datasets = []
	const firstAxis = xAxis.value[0]
	const otherAxes = xAxis.value.slice(1)

	for (let series of validSeries) {
		const column = series.column || series
		const seriesOptions = series.series_options || {}
		for (let xAxis of otherAxes) {
			const axisData = props.data.map((d) => d[xAxis])
			const uniqueAxisData = [...new Set(axisData)]
			for (let axis of uniqueAxisData) {
				const data = props.data.filter((d) => d[xAxis] === axis).map((d) => d[column])
				datasets.push({
					label: `${column} (${axis})`,
					data,
					name: axis,
					series_options: seriesOptions,
				})
			}
		}
	}

	return datasets
})

const lineChartOptions = computed(() => {
	return getLineChartOptions(labels.value, datasets.value, props.options)
})
</script>

<template>
	<BaseChart :title="props.options.title" :options="lineChartOptions" />
</template>
