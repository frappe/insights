<script setup lang="ts">
import { useChartView } from './chart_view'
import ChartView from './ChartView.vue'

const props = defineProps<{ chart_name: string }>()

const chart = useChartView(props.chart_name)
chart.load()
</script>

<template>
	<div class="h-full w-full">
		<ChartView :chart="chart" />
	</div>
</template>
