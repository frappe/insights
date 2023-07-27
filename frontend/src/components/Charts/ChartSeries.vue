<template></template>

<script setup>
import { inject, watch } from 'vue'

const props = defineProps({ options: Object, default: () => ({}) })

const chartOptions = inject('options')
if (!chartOptions.series) {
	chartOptions.series = []
}

watch(() => props.options, updateOptions, { deep: true, immediate: true })
function updateOptions(newOptions) {
	const existingSeries = chartOptions.series.find((series) => series.name === newOptions.name)
	if (existingSeries) {
		Object.assign(existingSeries, newOptions)
	} else {
		chartOptions.series.push(newOptions)
	}
}
</script>
