<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import { computed, watch } from 'vue'
import ChartBody from '../charts/components/ChartBody.vue'
import { __ } from '../translation'
import { useViewerChart, ViewerFilters } from './viewer'

// One chart card, on a dashboard grid or on its own. It owns its whole
// lifecycle — its own request, its own skeleton, its own failure — so a card
// that cannot load leaves every other card on the page alone.
const props = defineProps<{
	chart: string
	// the dashboard the card sits on. It carries the chart's audience, and it is
	// what lets filter state reach the query — a chart named on its own has no
	// filters to route.
	dashboard?: string
	filters?: ViewerFilters
}>()

const viewer = computed(() =>
	useViewerChart(props.chart, {
		dashboard: props.dashboard,
		filters: () => props.filters,
	}),
)

watch(viewer, (current) => current.load(), { immediate: true })
watch(
	() => props.filters,
	() => viewer.value.load(),
	{ deep: true },
)
</script>

<template>
	<div class="h-full w-full">
		<div
			v-if="viewer.failed.value"
			class="flex h-full w-full flex-col items-center justify-center gap-1 rounded border border-outline-gray-2 bg-surface-base"
		>
			<AlertTriangle class="h-6 w-6 text-ink-gray-4" stroke-width="1" />
			<p class="text-p-base text-ink-gray-5">{{ __('This chart is not available') }}</p>
		</div>

		<div
			v-else-if="!viewer.loaded.value"
			class="h-full w-full animate-pulse rounded border border-outline-gray-2 bg-surface-gray-2"
		/>

		<ChartBody v-else :chart="viewer.chart" />
	</div>
</template>
