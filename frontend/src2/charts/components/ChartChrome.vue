<script setup lang="ts">
import { ChartCard } from 'frappe-ui/charts'
import { computed } from 'vue'
import { rendersOwnCards } from '../adapter'
import type { ChartRead } from '../chart_view'
import type { ChartSegmentClick } from '../drill/segment_click'
import ChartBody from './ChartBody.vue'

// The chrome around an Insights chart: the card, the title and whatever the
// host puts beside the title through `#actions`. Inside it is
// ChartBody, which renders the chart and nothing else, so a host with chrome of
// its own — a desk island — mounts the body instead and gets no second border
// and no second title.
const props = defineProps<{
	chart: ChartRead
	/** Which reading to show, for a Number Chart. See `ChartBody`. */
	reading?: string
	readonly?: boolean
	filtered?: boolean
}>()

const emit = defineEmits<{
	segmentClick: [click: ChartSegmentClick]
	resetFilters: []
}>()

const card = computed(() => !rendersOwnCards(props.chart.doc.chart_type))
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<div class="min-h-0 w-full flex-1">
			<!-- `--chart-card-inset` is this card's own horizontal padding, named so
			     that a filler running to the card edge measures against it. Unset,
			     which is what a body with no card around it reads, the bleed is
			     nothing. -->
			<ChartCard
				class="h-full border-outline-gray-2"
				:class="card ? '[--chart-card-inset:1rem]' : undefined"
				:card="card"
			>
				<ChartBody
					:chart="props.chart"
					:title="props.chart.doc.title"
					:reading="props.reading"
					:readonly="props.readonly"
					:filtered="props.filtered"
					@segment-click="emit('segmentClick', $event)"
					@reset-filters="emit('resetFilters')"
				>
					<template v-if="$slots.actions" #actions>
						<slot name="actions" />
					</template>
				</ChartBody>
			</ChartCard>
		</div>
	</div>
</template>
