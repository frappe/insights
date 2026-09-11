<script setup lang="ts">
import { call } from 'frappe-ui'
import { waitUntil } from '../helpers'
import useChart from './chart'
import { useSharedChart } from './chart_read'
import ChartCardFrame from './components/ChartCardFrame.vue'

// A chart on its own page, for whoever the link reaches. It reads the saved
// chart through the public endpoint, so it draws the card read-only.
const props = defineProps<{ chart_name: string }>()

const chart_name = await call('insights.api.shared.get_chart_name', {
	chart_name: props.chart_name,
})

const chart = useChart(chart_name)
await waitUntil(() => chart.isloaded)

const read = useSharedChart(chart)
read.load()
</script>

<template>
	<div class="h-full w-full">
		<ChartCardFrame :chart="read" readonly />
	</div>
</template>
