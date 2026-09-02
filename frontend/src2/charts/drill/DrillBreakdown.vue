<script setup lang="ts">
import { ChartCard } from 'frappe-ui/charts'
import { computed } from 'vue'
import { EMPTY_RESULT } from '../../query/helpers'
import type { QueryResult } from '../../types/query.types'
import { adaptChart } from '../adapter'
import { breakdownChart } from './breakdown_chart'
import type { DrillLevelData } from './drill_stack'
import { segmentClickEvents, type ChartSegmentClick, type ClickPoint } from './segment_click'

// One breakdown level: the clicked Measure across the chosen Dimension, drawn by
// the chart the answer's own reading calls for. It goes through `adaptChart` like
// any card, so a click inside it comes back through the same resolver a card's
// click does — which is what makes the next level ride a path that already exists.
//
// Which measures the level holds is the answer's to say, not the caller's: a
// click on a number card named none of them and kept them all.
const props = defineProps<{
	answer: DrillLevelData
	dimension: string
}>()

const emit = defineEmits<{ segmentClick: [click: ChartSegmentClick] }>()

const chart = computed(() => breakdownChart(props.dimension, props.answer))

const result = computed<QueryResult>(() => ({
	...EMPTY_RESULT,
	columns: props.answer.columns,
	rows: props.answer.rows,
}))

const filler = computed(() =>
	adaptChart({
		chart_type: chart.value.chart_type,
		config: chart.value.config,
		result: result.value,
		readonly: true,
	}),
)

let clickedAt: ClickPoint = { x: 0, y: 0 }
function rememberPoint(event: MouseEvent) {
	clickedAt = { x: event.clientX, y: event.clientY }
}

const events = computed(() =>
	segmentClickEvents(filler.value, result.value.columns, (target) =>
		emit('segmentClick', { target, point: clickedAt }),
	),
)
</script>

<template>
	<!-- `card: false` keeps the box a chart needs — it clips the plot — and drops
	     the surface a card wears. A dialog is already the frame here, and a second
	     border inside it draws a card that is not there. -->
	<ChartCard class="h-full" :card="false" @click.capture="rememberPoint">
		<component v-if="filler" :is="filler.component" v-bind="filler.props" v-on="events" />
	</ChartCard>
</template>
