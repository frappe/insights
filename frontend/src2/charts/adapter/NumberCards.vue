<script setup lang="ts">
import type { NumberCardClickEvent, NumberCardEntry } from './number'
import NumberReading from './NumberReading.vue'
import type { ChartFailure } from './types'

// The readings a Number Chart draws, in a row. Nothing here decorates — it lays
// them out and passes a click on.
//
// A dashboard cell names one reading, so on a dashboard this row holds a single
// card and is that card. The workbook editor names none, so there it holds every
// reading the chart states and previews them side by side. It is a preview and
// not a layout: what a reading looks like on a dashboard is a cell of its own,
// which is the row of one.
//
// A cell was sized from this config — `numberCardRows` is the other half of
// that rule — so on a dashboard the one card fills it. The editor has no cell,
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
	<div class="flex h-full w-full flex-col gap-2">
		<!-- A Number Chart has no card to head, so the acts a host passes sit over
		     the readings instead of beside a title. The row is one button tall:
		     there is no title line here for the buttons to center on, and the
		     card around this clips at its edge. -->
		<div v-if="$slots.actions" class="flex h-7 shrink-0 items-center justify-end">
			<slot name="actions" />
		</div>

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
	</div>
</template>
