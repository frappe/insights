<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { __ } from '../translation'
import type { ChartView } from './chart_view'
import ChartChrome from './components/ChartChrome.vue'
import ChartDrillDown from './drill/ChartDrillDown.vue'
import type { ChartSegmentClick } from './drill/segment_click'

// One chart a reader gets, on a dashboard grid or on its own.
//
// The read is handed over rather than made here, because several cells can draw
// one chart — a Number chart is one cell per reading — and the rows behind them
// are one request. Whoever owns the page owns the read.
//
// It draws an Insights card by default and offers the chart to whoever wants a
// different frame. A host that frames the chart itself — a desk widget — fills
// the slot with the body alone, and gets the same drill without a second border
// around it.
const props = defineProps<{
	// absent while the page is still loading, and for a cell naming a chart that
	// is no longer there
	chart?: ChartView
	/** Which reading to draw, for a Number chart. */
	reading?: string
	// whether a filter currently reaches this card, so an empty one can say why
	filtered?: boolean
}>()

const emit = defineEmits<{ resetFilters: [] }>()

// The read says whether a drill leads anywhere: an anonymous reader is not
// offered one, and the endpoint refuses Guest as well. This check keeps the app
// from drawing a control that would only answer with a refusal.
const clicked = ref<ChartSegmentClick>()
function onSegmentClick(click: ChartSegmentClick) {
	if (!props.chart?.drillable) return
	clicked.value = click
}

// A new card is a new drill: the stack belongs to the click that started it.
watch(
	() => props.chart,
	() => (clicked.value = undefined),
)
</script>

<template>
	<div class="h-full w-full">
		<!-- read-only: sorting is a query, and a reader has no way to ask for one.
		     It is also what picks the reader's half of every message the chart has. -->
		<slot v-if="chart" :chart="chart" :on-segment-click="onSegmentClick">
			<ChartChrome
				:chart="chart"
				:reading="props.reading"
				readonly
				:filtered="props.filtered"
				@segment-click="onSegmentClick"
				@reset-filters="emit('resetFilters')"
			>
				<template v-if="$slots.actions" #actions><slot name="actions" /></template>
			</ChartChrome>
		</slot>

		<!-- not one of the card's states: a cell that names no chart has no store
		     to be loading, failed or empty. The layout is wrong, not a read. -->
		<div
			v-else
			class="flex h-full flex-1 flex-col items-center justify-center rounded-4 border border-outline-gray-2"
		>
			<div class="flex items-center gap-1.5 text-p-base text-ink-gray-4">
				<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
				<span>{{ __('Chart not found') }}</span>
			</div>
		</div>

		<!-- keyed on the click, so every drill starts from an empty stack -->
		<ChartDrillDown
			v-if="clicked && chart"
			:subject="chart.drillSubject"
			:clicked="clicked"
			@close="clicked = undefined"
		/>
	</div>
</template>
