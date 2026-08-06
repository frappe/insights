<script setup lang="ts">
import { AlertTriangle, RefreshCcw } from 'lucide-vue-next'
import { computed, watch } from 'vue'
import ChartBody from '../charts/components/ChartBody.vue'
import ChartTitle from '../charts/components/ChartTitle.vue'
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
	useViewerChart(props.chart, {
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
	() => viewer.value.executedAt.value,
	(executedAt) => executedAt && emit('loaded', executedAt),
)
</script>

<template>
	<div class="h-full w-full">
		<div
			v-if="viewer.failed.value"
			class="flex h-full w-full flex-col items-center justify-center gap-2 rounded border border-outline-gray-2 bg-surface-base"
		>
			<AlertTriangle class="h-6 w-6 text-ink-gray-4" stroke-width="1" />
			<p class="text-p-base text-ink-gray-5">{{ __('This chart is not available') }}</p>
			<Button variant="outline" :label="__('Retry')" @click="viewer.load(true)">
				<template #prefix>
					<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</template>
			</Button>
		</div>

		<div
			v-else-if="!viewer.loaded.value"
			class="h-full w-full animate-pulse rounded border border-outline-gray-2 bg-surface-gray-2"
		/>

		<!-- a card with no rows says so itself: the builder's empty state talks
		     about configuring the chart, which is not this reader's problem -->
		<div
			v-else-if="viewer.empty.value"
			class="flex h-full w-full flex-col overflow-hidden rounded border border-outline-gray-2 bg-surface-base"
		>
			<ChartTitle :title="viewer.chart.doc.title" />
			<div class="flex flex-1 flex-col items-center justify-center gap-2 p-2">
				<p class="text-p-base text-ink-gray-5">{{ __('No data') }}</p>
				<Button
					v-if="filtered"
					variant="outline"
					:label="__('Reset filters')"
					@click="emit('resetFilters')"
				/>
			</div>
		</div>

		<!-- read-only: sorting is a query, and a viewer has no way to ask for one -->
		<ChartBody v-else :chart="viewer.chart" readonly />
	</div>
</template>
