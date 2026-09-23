<script setup lang="ts">
import { AlertTriangle, Lock } from 'lucide-vue-next'
import { computed } from 'vue'
import type { ChartFailure } from '../adapter/types'

// What a card says where its picture would be, when there is no picture: the
// failure, and the refusal a reader cannot act on. One block for both, so "Could
// not load" and "Not Permitted" read as one family whichever chart type draws
// them — the chrome around a plot, and a Number Chart's reading, which is its
// own chrome.
//
// `status` and not `alert`: a dashboard can fail eight cards at once, and eight
// interruptions say less than one line each.
//
// It aligns nothing itself. The chrome centres what it draws over the plot, and
// a reading's card runs its blocks down the start edge, so the host's own class
// says which.
const props = defineProps<{
	failure: ChartFailure
	/**
	 * Draw the reason under the headline. A card one line tall — a reading —
	 * leaves it off, and the whole of it still waits in the tooltip.
	 */
	detailed?: boolean
}>()

const refused = computed(() => props.failure.kind === 'notPermitted')
</script>

<template>
	<div
		class="flex min-h-0 max-w-full flex-col gap-2"
		role="status"
		:title="props.failure.detailText"
	>
		<div
			class="flex min-w-0 shrink-0 items-center gap-1.5 text-p-sm"
			:class="refused ? 'text-ink-gray-7' : 'text-ink-gray-8'"
		>
			<!-- The size of the text it stands beside, here and in every other
			     state Insights draws: an icon larger than its sentence reads as a
			     picture of an error, not as part of the line that states one. -->
			<component
				:is="refused ? Lock : AlertTriangle"
				class="h-3.5 w-3.5 shrink-0"
				:class="refused ? 'text-ink-gray-5' : 'text-ink-red-5'"
				stroke-width="1.5"
			/>
			<span class="truncate">{{ props.failure.headline }}</span>
		</div>

		<!-- The whole message is in the tooltip, so the clamp costs the reader
		     nothing but a hover. -->
		<p
			v-if="props.detailed && props.failure.detailText"
			class="line-clamp-2 px-4 text-p-xs text-ink-gray-5"
		>
			{{ props.failure.detailText }}
		</p>

		<!-- The act, for a card with room under the message. A reading puts its
		     own in the title row instead. -->
		<slot />
	</div>
</template>
