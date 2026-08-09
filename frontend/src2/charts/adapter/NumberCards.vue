<script setup lang="ts">
import { NumberCard } from 'frappe-ui/charts'
import { computed } from 'vue'
import type { NumberCardClickEvent, NumberCardEntry } from './number'

// The grid a Number Chart's readings sit in. It is a filler like any other: the
// card around it is the chrome `ChartBody` draws, which is why every card in it
// draws no surface of its own. Nothing here decorates — it lays the readings
// out and reports a click.
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
				<NumberCard v-bind="reading.card" :card="false" />
			</div>
		</div>
	</div>
</template>
