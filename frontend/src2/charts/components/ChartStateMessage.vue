<script setup lang="ts">
import { AlertTriangle, Lock } from 'lucide-vue-next'
import { computed } from 'vue'
import type { ChartFailure } from '../adapter/types'

// What a card shows in place of the plot: an error, or a refusal the reader
// cannot act on. Both use this one block, so "Could not load" and "Not
// Permitted" look alike in every chart type: in the chrome around a plot, and in
// a Number Chart's reading, which has its own chrome.
//
// `status` and not `alert`: a dashboard can fail eight cards at once, and eight
// interruptions say less than one line each.
//
// It sets no alignment. The chrome centres it over the plot, and a reading's
// card aligns it to the start edge, so the host's class decides.
const props = defineProps<{
	failure: ChartFailure
	/**
	 * Show the reason under the headline. A one-line card, such as a reading,
	 * leaves it out, and the full reason stays in the tooltip.
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
			<!-- The icon matches the text size, here and in every other state
			     Insights shows. A larger icon reads as an image of an error, not
			     as part of the sentence. -->
			<component
				:is="refused ? Lock : AlertTriangle"
				class="h-3.5 w-3.5 shrink-0"
				:class="refused ? 'text-ink-gray-5' : 'text-ink-red-5'"
				stroke-width="1.5"
			/>
			<span class="truncate">{{ props.failure.headline }}</span>
		</div>

		<!-- The whole message is in the tooltip, so the clamp costs the reader
		     only a hover. -->
		<p
			v-if="props.detailed && props.failure.detailText"
			class="line-clamp-2 px-4 text-p-xs text-ink-gray-5"
		>
			{{ props.failure.detailText }}
		</p>

		<slot />
	</div>
</template>
