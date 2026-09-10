<script setup lang="ts">
import ChartBody from '../charts/components/ChartBody.vue'
import { useChartView } from '../charts/chart_view'
import ChartView from '../charts/ChartView.vue'

// One chart inside another app. The body is all this island is: the host frames
// it itself — the border, the title, the menu — and the host's frame wins, so it
// fills `ChartView`'s slot with the body alone and draws no card of its own.
//
// It reports nothing. A widget is less than a page, so it has no header of its
// own to fill: desk heads it with the name its own document carries, which is
// not always the Insights chart's title, and one label is the point.
const props = defineProps<{ chart: string }>()

const shown = useChartView(props.chart)
shown.load()
</script>

<template>
	<ChartView :chart="shown" v-slot="{ chart, onSegmentClick }">
		<!-- no `title`: the host prints its own. No `filtered`: nothing here owns
		     filter state, so an empty chart has no reset to offer -->
		<ChartBody :chart="chart" readonly @segment-click="onSegmentClick" />
	</ChartView>
</template>
