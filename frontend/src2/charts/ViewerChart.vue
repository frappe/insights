<script setup lang="ts">
import { computed, watch } from 'vue'
import ChartBody from './components/ChartBody.vue'
import type { ViewerFilters } from '../dashboard/viewer'
import { useSavedChart } from './chart_read'

// One chart card, on a dashboard grid or on its own. It owns its whole
// lifecycle — its own request, its own reloads — so a card that cannot load
// leaves every other card on the page alone. What it shows while it has no
// picture is the card's own business, and ChartBody is the card.
const props = defineProps<{
	chart: string
	// the dashboard the card sits on. It carries the chart's audience, and it is
	// what lets filter state reach the query — a chart named on its own has no
	// filters to route.
	dashboard?: string
	// only the filters that reach this card, so an empty card can say whether a
	// filter is the reason
	filters?: ViewerFilters
	// where this card sits on the grid. The execution queue serves the lowest
	// first, so a throttled page fills in from the top.
	priority?: number
	// bumped by the page's refresh action
	refreshToken?: number
}>()

const emit = defineEmits<{ loaded: [executedAt: Date]; resetFilters: [] }>()

const viewer = computed(() =>
	useSavedChart(props.chart, {
		dashboard: props.dashboard,
		filters: () => props.filters,
		priority: props.priority,
	}),
)

const filtered = computed(() => Boolean(props.filters && Object.keys(props.filters).length))

watch(viewer, (current) => current.load(), { immediate: true })

// by content, not by identity: the page hands each card a fresh object whenever
// any filter moves, and only the cards this one reaches should fetch again
watch(
	() => JSON.stringify(props.filters || {}),
	() => viewer.value.load(),
)

watch(
	() => props.refreshToken,
	() => viewer.value.load(true),
)

watch(
	() => viewer.value.executedAt,
	(executedAt) => executedAt && emit('loaded', executedAt),
)
</script>

<template>
	<div class="h-full w-full">
		<!-- read-only: sorting is a query, and a viewer has no way to ask for one.
		     It is also what picks the reader's half of every message the card has. -->
		<ChartBody
			:chart="viewer"
			readonly
			:filtered="filtered"
			@reset-filters="emit('resetFilters')"
		/>
	</div>
</template>
