<script setup lang="ts">
import { ChartCard } from 'frappe-ui/charts'
import { computed } from 'vue'
import { drawsOwnCards } from '../adapter'
import { ChartRead } from '../chart_read'
import type { ChartSegmentClick } from '../drill/segment_click'
import ChartBody from './ChartBody.vue'

// The card an Insights surface puts a chart in: the surface and the title. Inside
// it is ChartBody, which draws the chart and nothing else, so a host with a frame
// of its own — a desk widget — mounts the body instead and gets no second border
// and no second title.
const props = defineProps<{
	chart: ChartRead
	/** Which reading to draw, for a Number Chart. See `ChartBody`. */
	column?: string
	readonly?: boolean
	filtered?: boolean
}>()

const emit = defineEmits<{
	segmentClick: [click: ChartSegmentClick]
	resetFilters: []
}>()

const card = computed(() => !drawsOwnCards(props.chart.doc.chart_type))
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<div class="min-h-0 w-full flex-1">
			<!-- `--chart-card-inset` is this card's own horizontal padding, named so
			     that a filler running to the card edge measures against it. Unset,
			     which is what a body with no card around it reads, the bleed is
			     nothing. -->
			<ChartCard
				class="h-full"
				:class="card ? '[--chart-card-inset:1rem]' : undefined"
				:card="card"
			>
				<ChartBody
					:chart="props.chart"
					:title="props.chart.doc.title"
					:column="props.column"
					:readonly="props.readonly"
					:filtered="props.filtered"
					@segment-click="emit('segmentClick', $event)"
					@reset-filters="emit('resetFilters')"
				/>
			</ChartCard>
		</div>
	</div>
</template>
