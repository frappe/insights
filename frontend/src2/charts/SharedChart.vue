<script setup lang="ts">
import { useChartView } from './chart_view'
import ChartView from './ChartView.vue'

// A chart on its own page, for whoever the link reaches. It is a view surface
// like any other, so it carries nothing but the reference the URL names.
const props = defineProps<{ chart_name: string }>()

const chart = useChartView(props.chart_name)
chart.load()
</script>

<template>
	<div class="h-full w-full">
		<ChartView :chart="chart" />
	</div>
</template>
