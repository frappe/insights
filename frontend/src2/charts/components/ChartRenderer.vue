<script setup lang="ts">
import { ref, watch } from 'vue'
import { ChartRead } from '../chart_read'
import AuthoringDrillDown from '../drill/AuthoringDrillDown.vue'
import type { ChartSegmentClick } from '../drill/segment_click'
import ChartChrome from './ChartChrome.vue'

// The chart with the affordance the builder and the SPA give it: drill into the
// rows behind a segment. The card itself is ChartChrome.
const props = defineProps<{
	chart: ChartRead
	reading?: string
	hideMaximize?: boolean
	actionsRevealed?: boolean
	/** Whether the reader narrowed these rows, and can take that back. */
	filtered?: boolean
}>()

const emit = defineEmits<{
	resetFilters: []
}>()

// The author's drill is the reader's drill plus "open as query" — one dialog,
// two feeds. What the card's store was built from decides which endpoint answers
// a level, so nothing here says.
const clicked = ref<ChartSegmentClick>()
// a new card is a new drill: the stack belongs to the click that started it
watch(
	() => props.chart,
	() => (clicked.value = undefined),
)
</script>

<template>
	<ChartChrome
		:chart="props.chart"
		:reading="props.reading"
		:filtered="props.filtered"
		:hide-maximize="props.hideMaximize"
		:actions-revealed="props.actionsRevealed"
		@segment-click="clicked = $event"
		@reset-filters="emit('resetFilters')"
	>
		<template v-if="$slots.actions" #actions="{ expanded }">
			<slot name="actions" :expanded="expanded" />
		</template>
		<template v-if="$slots.hoverActions" #hoverActions>
			<slot name="hoverActions" />
		</template>
	</ChartChrome>

	<!-- `v-if` unmounts it on close, so every drill starts from an empty stack -->
	<AuthoringDrillDown
		v-if="clicked"
		:subject="props.chart.drillSubject"
		:clicked="clicked"
		:adhoc-filters="props.chart.routedFilters"
		@close="clicked = undefined"
	/>
</template>
