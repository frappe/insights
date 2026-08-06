<script setup lang="ts">
import ViewerChart from '../charts/ViewerChart.vue'
import type { ViewerFilters } from '../dashboard/viewer'

// The card is all this island is. Everything it does — load, skeleton, degrade —
// is what a card on the dashboard grid does, so the two share one component.
defineProps<{ chart: string; dashboard?: string; filters?: ViewerFilters }>()
</script>

<template>
	<ViewerChart :chart="chart" :dashboard="dashboard" :filters="filters" />
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
