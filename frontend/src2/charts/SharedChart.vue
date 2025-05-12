<script setup lang="ts">
import { call } from 'frappe-ui'
import useChart from './chart'
import ChartRenderer from './components/ChartRenderer.vue'

const props = defineProps<{ chart_name: string }>()

const chart_name = await call('insights.api.shared.get_chart_name', {
	chart_name: props.chart_name,
})

const chart = useChart(chart_name)
chart.refresh()
</script>

<template>
	<div class="h-full w-full">
		<ChartRenderer :chart="chart" />
	</div>
</template>
