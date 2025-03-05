<script setup lang="ts">
import useChart from './chart'
import ChartRenderer from './components/ChartRenderer.vue'

const props = defineProps<{ chart_name: string }>()

const chart = useChart(props.chart_name)
chart.refresh()
</script>

<template>
	<div class="h-full w-full">
		<ChartRenderer :chart="chart" />
	</div>
</template>
