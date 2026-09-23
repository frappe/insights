<script setup lang="ts">
import { Button } from 'frappe-ui'
import { ChartCard, ChartContainer } from 'frappe-ui/charts'
import { __ } from '../../translation'
import type { ChartFailure } from '../adapter/types'
import ChartStateMessage from '../components/ChartStateMessage.vue'

// The drill's body before there is a level to draw in it, in the shape of the
// plot rather than a spinner turning in an empty box. It is the same box either
// way the body is not ready: the level's own read, and the chunk a surface
// loads its rows pane from.
//
// What it says where the plot would be comes from the same block a card draws
// its states with, so "Could not load" and "Not Permitted" read as one family
// whether the reader is looking at a card or at a level under it.
const props = withDefaults(
	defineProps<{
		loading?: boolean
		/** what to say instead, for a level that will not draw */
		failure?: ChartFailure | null
	}>(),
	{ loading: true, failure: null },
)

defineEmits<{ retry: [] }>()
</script>

<template>
	<ChartCard class="h-full" :card="false">
		<ChartContainer :loading="loading" :error="props.failure?.headline || null" :empty="true">
			<template #error>
				<div class="flex flex-col items-center gap-2">
					<ChartStateMessage :failure="props.failure!" detailed class="items-center" />
					<!-- The first level has no crumb to go back to, so without this the
					     only way out is closing the card. A refusal is an answer: the
					     reader owns no grant they could change, and asking again would
					     be refused the same way. -->
					<Button
						v-if="props.failure?.kind !== 'notPermitted'"
						variant="outline"
						:label="__('Retry')"
						@click="$emit('retry')"
					/>
				</div>
			</template>
		</ChartContainer>
	</ChartCard>
</template>
