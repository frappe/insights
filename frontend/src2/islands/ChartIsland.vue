<script setup lang="ts">
import ChartBody from '../charts/components/ChartBody.vue'
import { useChartView } from '../charts/chart_view'
import ChartView from '../charts/ChartView.vue'

// One chart inside a host page. The host renders the frame: the border, the
// title and the menu. So the island fills `ChartView`'s slot with the chart body
// only and renders no card of its own.
//
// It emits no title and no actions. A desk widget has no header to fill. Desk
// labels the widget with its own document's name, which can differ from the
// Insights chart's title, and the widget should show one label only.
const props = defineProps<{ chart: string }>()

const shown = useChartView(props.chart)
shown.load()
</script>

<template>
	<ChartView :chart="shown" v-slot="{ chart, onSegmentClick }">
		<!-- No `title`: the host shows its own. No `filtered`: nothing here holds
		     filter state, so an empty chart has nothing to reset -->
		<ChartBody :chart="chart" readonly @segment-click="onSegmentClick" />
	</ChartView>
</template>
