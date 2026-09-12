<script setup lang="ts">
import { waitUntil } from '../helpers'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import useChart from './chart'
import { useSharedChart } from './chart_read'
import ChartCardFrame from './components/ChartCardFrame.vue'

// A chart on its own page, for whoever the link reaches. It reads the saved
// chart through the public endpoint, so it draws the card read-only.
const props = defineProps<{ chart_name: string }>()

const chart = useChart(props.chart_name)
const read = useSharedChart(chart)
waitUntil(() => !chart.pending).then(() => read.load())
</script>

<template>
	<div class="relative h-full w-full">
		<LoadingOverlay v-if="chart.pending" />
		<ChartCardFrame v-else :chart="read" readonly />
	</div>
</template>
