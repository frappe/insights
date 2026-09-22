<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import { waitUntil } from '../helpers'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { __ } from '../translation'
import useChart from './chart'
import { useSharedChart } from './chart_read'
import ChartChrome from './components/ChartChrome.vue'

// A chart on its own page, for whoever the link reaches. It reads the saved
// chart through the public endpoint, so it draws the card read-only.
const props = defineProps<{ chart_name: string }>()

const chart = useChart(props.chart_name)
const read = useSharedChart(chart)
waitUntil(() => !chart.pending || chart.failed).then(() => {
	if (!chart.failed) read.load()
})
</script>

<template>
	<div class="relative h-full w-full">
		<div v-if="chart.failed" class="flex h-full w-full items-center justify-center">
			<div class="flex items-center gap-1.5 text-p-base text-ink-gray-4">
				<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
				<span>{{ __('Chart not found') }}</span>
			</div>
		</div>
		<LoadingOverlay v-else-if="chart.pending" />
		<ChartChrome v-else :chart="read" readonly />
	</div>
</template>
