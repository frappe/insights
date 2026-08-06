<script setup lang="ts">
import ViewerChart from '../charts/ViewerChart.vue'
import type { DashboardCellProps } from './viewer'

// One cell of a dashboard grid, as a reader gets it. A chart card owns its own
// request and its own states, so a cell that cannot load leaves the page alone.
const props = defineProps<DashboardCellProps>()

defineEmits<{ loaded: [executedAt: Date]; resetFilters: [] }>()
</script>

<template>
	<div class="flex h-full w-full items-center justify-start p-2">
		<ViewerChart
			v-if="props.item.type === 'chart'"
			:chart="props.item.chart!"
			:dashboard="props.dashboard"
			:filters="props.filters"
			:priority="props.priority"
			:refresh-token="props.refreshToken"
			@loaded="$emit('loaded', $event)"
			@reset-filters="$emit('resetFilters')"
		/>
		<div
			v-else-if="props.item.type === 'text'"
			class="prose prose-v3 h-full w-full max-w-none overflow-auto text-ink-gray-7"
			v-html="props.item.text"
		/>
	</div>
</template>
