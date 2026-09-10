<script setup lang="ts">
import { Button } from 'frappe-ui'
import { NumberCard } from 'frappe-ui/charts'
import { AlertTriangle, RefreshCcw } from 'lucide-vue-next'
import { computed } from 'vue'
import { __ } from '../../translation'
import type { NumberCardClickEvent, NumberCardEntry } from './number'
import type { ChartFailure } from './types'

// One reading of a Number Chart. Nothing here decorates — it fills the space it
// was given and reports a click.
//
// The reading is a card of frappe-ui's, drawn with its own surface, which is why
// the filler tells the chrome to draw none: a card inside a card would border
// the reading twice.
//
// This card is also where the chart wears its states, because it is the only
// surface it has. So it stands in every state: it skeletons while the query
// runs, prints a dash when it returns nothing, and carries the failure and the
// retry when it fails. A reader who sees a titled card and a dash has been told
// which reading is missing, which a message floating on the page never said.
const props = defineProps<{
	card: NumberCardEntry
	/** Stand at cell size rather than fill the cell. See `NumberCards`. */
	preview?: boolean
	loading?: boolean
	failure?: ChartFailure | null
}>()

const emit = defineEmits<{
	// eslint-disable-next-line no-unused-vars
	cardClick: [event: NumberCardClickEvent]
	retry: []
}>()

// `column` is what a drill names, `missing` stands in for the reading it names,
// and `height` is the row's to apply, so none of them is something the card draws.
const reading = computed(() => {
	// eslint-disable-next-line no-unused-vars
	const { column, missing, height, ...card } = props.card
	return card
})

// A cell naming a reading the chart no longer states is the card's own failure,
// and the only one nothing can be done about: the query still runs, and running
// it again will not bring the Measure back. So the message stands without the
// retry beside it, and it is the author who removes the cell.
const failure = computed<ChartFailure | null>(() =>
	props.card.missing
		? { headline: __('Reading not found'), detailHtml: '' }
		: props.failure || null,
)
const retryable = computed(() => Boolean(props.failure) && !props.card.missing)
const drillable = computed(() => !props.card.missing)
</script>

<template>
	<div
		class="min-w-0"
		:class="[
			preview ? 'shrink-0 basis-[calc(20%-0.8rem)]' : 'flex-1',
			drillable ? 'cursor-pointer' : undefined,
		]"
		:style="preview ? { height: `${card.height}px` } : undefined"
		@click="drillable && emit('cardClick', { column: card.column })"
	>
		<NumberCard
			v-bind="reading"
			class="h-full"
			:loading="props.loading && !card.missing"
			:error="failure?.headline"
		>
			<!-- One line, because the cell's height is the card's own and any
			     taller block is a block the card cuts in half. The whole of it
			     waits on hover. -->
			<template v-if="failure" #error>
				<div
					class="flex items-center gap-1.5 text-p-sm text-ink-gray-8"
					:title="failure.detailText"
				>
					<!-- Both icons on the card are the size of the text beside them,
					     so neither reads as an ornament on the line. -->
					<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
					<span class="truncate">{{ failure.headline }}</span>
				</div>
			</template>

			<!-- The retry rides the title row, which stands at zero height, so the
			     action costs the message none of the card. It is the smallest
			     control in the library for the same reason: one taller than the
			     title's line stands outside the row and reads as though the card is
			     padded less at the top. `-me-1.5` gives back the button's own
			     inset, so it is the glyph and not its hit box that stands the
			     card's own distance from the edge. -->
			<template v-if="retryable" #actions>
				<Button
					class="-me-1.5"
					variant="ghost"
					size="xs"
					:title="__('Retry')"
					@click.stop="emit('retry')"
				>
					<template #icon>
						<RefreshCcw class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
			</template>
		</NumberCard>
	</div>
</template>
