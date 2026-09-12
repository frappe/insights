<script setup lang="ts">
import type { NumberCardClickEvent, NumberCardEntry } from './number'
import NumberReading from './NumberReading.vue'
import type { ChartFailure } from './types'

// The readings a Number Chart draws, in a row. Nothing here decorates — it lays
// them out and passes a click on.
//
// A dashboard cell names one reading, so on a dashboard this row holds a single
// card and is that card. The workbook editor names none, so there it holds every
// reading the chart states and previews them side by side.
//
// `numberCardRows` sizes the cell from this config, so on a dashboard the one
// card fills it. The editor has no cell,
// so there each card is drawn at the size a cell would give it: the height the
// rule states, and a fifth of the pane wide, which is the width a dropped cell
// starts at.
//
// The gap is the one a dashboard puts between two cells — 16px, the `p-2` each
// grid cell carries on both sides — so a preview of two readings and two cells
// side by side stand the same distance apart.
defineProps<{
	cards: NumberCardEntry[]
	/** Draw every card at cell size, for a surface with no cell to fill. */
	preview?: boolean
	loading?: boolean
	failure?: ChartFailure | null
}>()

const emit = defineEmits<{
	// eslint-disable-next-line no-unused-vars
	cardClick: [event: NumberCardClickEvent]
	retry: []
}>()
</script>

<template>
	<div class="relative flex h-full w-full flex-col">
		<div class="flex w-full gap-4" :class="preview ? 'flex-wrap content-start' : 'h-full'">
			<NumberReading
				v-for="card in cards"
				:key="card.column"
				:card="card"
				:preview="preview"
				:loading="loading"
				:failure="failure"
				@card-click="emit('cardClick', $event)"
				@retry="emit('retry')"
			/>
		</div>

		<!-- A Number Chart has no card to head, so a host's actions sit over the
		     readings instead of beside a title. They take no height: the cell a
		     card is drawn in is sized from the config alone, so a row in the flow
		     would push the cards past its edge.

		     Drawn after the readings, because a reading is a card with a surface
		     of its own and both boxes are positioned — the later one paints over
		     the earlier, which is what puts these on top without a z-index. -->
		<div v-if="$slots.actions" class="absolute top-0 right-0 flex items-center p-2">
			<slot name="actions" />
		</div>
	</div>
</template>
