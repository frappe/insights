<script setup lang="ts">
import { NumberCard } from 'frappe-ui/charts'
import { computed } from 'vue'
import type { NumberCardClickEvent, NumberCardEntry } from './number'

// The grid a Number Chart's readings sit in. Nothing here decorates — it lays
// the readings out and reports a click.
//
// Every reading is a card of frappe-ui's, drawn with its own surface, which is
// why the filler tells the chrome to draw none: a grid of cards inside a card
// would border each reading twice. The cards fill the cell they are given
// rather than the height they need, so a row of them lines up and the author
// sets that height by resizing the item.
//
// The gap is the one a dashboard puts between two items — 16px, the `p-2` each
// grid cell carries on both sides. Two readings side by side and two charts side
// by side stand the same distance apart.
const props = defineProps<{ cards: NumberCardEntry[] }>()

const emit = defineEmits<{
	// eslint-disable-next-line no-unused-vars
	cardClick: [event: NumberCardClickEvent]
}>()

// `column` is the reading's identity, not a card prop, so it is kept out of
// what the card is handed.
const readings = computed(() => props.cards.map(({ column, ...card }) => ({ column, card })))
</script>

<template>
	<div class="h-full w-full @container">
		<div
			class="grid h-full w-full grid-cols-1 gap-4 @xs:grid-cols-2 @xl:grid-cols-3 @3xl:grid-cols-4 @4xl:grid-cols-5"
		>
			<div
				v-for="reading in readings"
				:key="reading.column"
				class="min-w-0 cursor-pointer"
				@dblclick="emit('cardClick', { column: reading.column })"
			>
				<NumberCard v-bind="reading.card" class="h-full" />
			</div>
		</div>
	</div>
</template>
