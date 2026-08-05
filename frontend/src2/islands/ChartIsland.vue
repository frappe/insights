<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import { computed, watch } from 'vue'
import useChart from '../charts/chart'
import ChartBody from '../charts/components/ChartBody.vue'
import { __ } from '../translation'
import { AdhocFilters } from '../types/query.types'

const props = defineProps<{ chart: string; filters?: AdhocFilters }>()

const chart = computed(() => useChart(props.chart))

// Either the document is on its way, or the load failed and there is nothing to
// render. The store reports both through the same two flags.
const loading = computed(() => chart.value.loading)
const failed = computed(() => !chart.value.loading && !chart.value.isloaded)

watch(
	[() => props.chart, () => props.filters, () => chart.value.isloaded],
	() => {
		const current = chart.value
		// A viewer never writes the chart back.
		current.autoSave = false
		if (!current.isloaded) return
		current.dataQuery.adhocFilters = props.filters
		current.refresh()
	},
	{ immediate: true, deep: true },
)
</script>

<template>
	<div class="h-full w-full">
		<div
			v-if="failed"
			class="flex h-full w-full flex-col items-center justify-center gap-1 rounded border border-outline-gray-2 bg-surface-base"
		>
			<AlertTriangle class="h-6 w-6 text-ink-gray-4" stroke-width="1" />
			<p class="text-p-base text-ink-gray-5">{{ __('This chart is not available') }}</p>
		</div>

		<div
			v-else-if="loading"
			class="h-full w-full animate-pulse rounded border border-outline-gray-2 bg-surface-gray-2"
		/>

		<ChartBody v-else :chart="chart" />
	</div>
</template>

<style>
/* The chart fills the element the host gives it, and a percentage height needs
   every ancestor to have one. The mount shell's own containers — the shadow host
   and the theme container Vue mounts into — sit between us and that element and
   are auto-height, which collapses the chart to its title. Both are inside this
   shadow root, so the island's own sheet is what can size them. */
:host,
.frappe-island-root {
	height: 100%;
}
</style>
