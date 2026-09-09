<script setup lang="ts">
import { Button } from 'frappe-ui'
import { NumberCard } from 'frappe-ui/charts'
import { AlertTriangle, RefreshCcw } from 'lucide-vue-next'
import { computed } from 'vue'
import { __ } from '../../translation'
import type { NumberCardClickEvent, NumberCardEntry } from './number'
import type { ChartFailure } from './types'

// The grid a Number Chart's readings sit in. Nothing here decorates — it lays
// the readings out and reports a click.
//
// Every reading is a card of frappe-ui's, drawn with its own surface, which is
// why the filler tells the chrome to draw none: a grid of cards inside a card
// would border each reading twice. A row packs to the height its cards need
// rather than stretching to fill the pane; cards within one row still equalize
// against each other, so the author's item height sets the columns, not the
// card height.
//
// The gap is the one a dashboard puts between two items — 16px, the `p-2` each
// grid cell carries on both sides. Two readings side by side and two charts side
// by side stand the same distance apart.
//
// The cards are also where this chart wears its states, because they are the only
// surface it has. So the grid stands in every state: the cards skeleton while the
// query runs, print a dash when it returns nothing, and carry the failure and the
// retry when it fails. A reader who sees a titled card and a dash has been told
// which reading is missing, which a message floating on the page never said.
const props = defineProps<{
	cards: NumberCardEntry[]
	loading?: boolean
	failure?: ChartFailure | null
}>()

const emit = defineEmits<{
	// eslint-disable-next-line no-unused-vars
	cardClick: [event: NumberCardClickEvent]
	retry: []
}>()

// `column` is the reading's identity in the grid, not something the card draws,
// so it is the one field held back from the card.
const readings = computed(() => props.cards.map(({ column, ...card }) => ({ column, card })))
</script>

<template>
	<div class="h-full w-full @container">
		<div
			class="grid h-full w-full auto-rows-min content-start grid-cols-1 gap-4 @xs:grid-cols-2 @xl:grid-cols-3 @3xl:grid-cols-4 @4xl:grid-cols-5"
		>
			<div
				v-for="reading in readings"
				:key="reading.column"
				class="min-w-0 cursor-pointer"
				@dblclick="emit('cardClick', { column: reading.column })"
			>
				<NumberCard
					v-bind="reading.card"
					class="h-full"
					:loading="props.loading"
					:error="props.failure?.headline"
				>
					<!-- One line, because the author sets the card's height and any
					     taller block is a block the card cuts in half. The reason
					     is the chart's and not this reading's — five cards printing
					     one sentence five times say it no better — so it waits on
					     hover, where the whole of it fits. -->
					<template v-if="props.failure" #error>
						<div
							class="flex items-center gap-1.5 text-p-sm text-ink-gray-8"
							:title="props.failure.detailText"
						>
							<!-- Both icons on the card are the size of the text beside
							     them, so neither reads as an ornament on the line. -->
							<AlertTriangle
								class="h-3.5 w-3.5 shrink-0 text-ink-red-5"
								stroke-width="1.5"
							/>
							<span class="truncate">{{ props.failure.headline }}</span>
						</div>
					</template>

					<!-- The retry rides the title row, which stands at zero height,
					     so the action costs the message none of the card. It is the
					     smallest control in the library for the same reason: one
					     taller than the title's line stands outside the row and
					     reads as though the card is padded less at the top.
					     `-me-1.5` gives back the button's own inset, so it is the
					     glyph and not its hit box that stands the card's own
					     distance from the edge. -->
					<template v-if="props.failure" #actions>
						<Button
							class="-me-1.5"
							variant="ghost"
							size="xs"
							:title="__('Retry')"
							@click="emit('retry')"
						>
							<template #icon>
								<RefreshCcw
									class="h-3.5 w-3.5 text-ink-gray-6"
									stroke-width="1.5"
								/>
							</template>
						</Button>
					</template>
				</NumberCard>
			</div>
		</div>
	</div>
</template>
