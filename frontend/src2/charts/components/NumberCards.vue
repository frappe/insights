<script setup lang="ts">
import type { NumberCardClickEvent, NumberCardEntry } from '../adapter/number'
import NumberReading from './NumberReading.vue'
import type { ChartFailure } from '../adapter/types'

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
	/** The query returned no rows. See `ChartBody`. */
	empty?: boolean
	/** Whether this surface's feed answers a drill. See `ChartBody`. */
	drillable?: boolean
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
				v-for="(card, index) in cards"
				:key="card.column"
				:card="card"
				:preview="preview"
				:loading="loading"
				:failure="failure"
				:empty="empty"
				:drillable="drillable"
				@card-click="emit('cardClick', $event)"
				@retry="emit('retry')"
			>
				<!-- A Number Chart has no card to head, so a host's actions go in
				     the first card's own action row. Over the readings instead,
				     they would paint over the Retry the failed card draws in the
				     same corner. A dashboard cell names one reading, so the first
				     card is the card. -->
				<template v-if="$slots.actions && index === 0" #actions>
					<slot name="actions" />
				</template>
			</NumberReading>
		</div>
	</div>
</template>
