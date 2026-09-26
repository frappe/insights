<script setup lang="ts">
import { Button } from 'frappe-ui'
import { ChartCard, ChartContainer } from 'frappe-ui/charts'
import { __ } from '../../translation'
import type { ChartFailure } from '../adapter/types'
import ChartStateMessage from '../components/ChartStateMessage.vue'

// The drill's body before its level is ready, shaped like the plot instead of a
// spinner in an empty box. It covers both waits: the level's own read, and the
// chunk that holds the rows pane.
const props = withDefaults(
	defineProps<{
		loading?: boolean
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
					     only way out is closing the card. A refusal gets no retry: the
					     reader cannot change their own permissions, and the server
					     would refuse again. -->
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
