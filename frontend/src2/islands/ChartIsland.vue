<script setup lang="ts">
import ChartBody from '../charts/components/ChartBody.vue'
import { useChartView } from '../charts/chart_view'
import ChartView from '../charts/ChartView.vue'

// One chart inside a host page. The host renders the card: the border, the
// title and the menu. So the island fills `ChartView`'s slot with the chart body
// only. A Number chart draws its readings as cards of their own unless the claim
// passes `card: false`, so the claim decides and the island knows no host.
//
// It emits no title and no actions. A desk widget has no header to fill. Desk
// labels the widget with its own document's name, which can differ from the
// Insights chart's title, and the widget should show one label only.
const props = withDefaults(
	defineProps<{
		chart: string
		/** `false`: the host draws the card and its label. See `ChartAdapterInput`. */
		card?: boolean
	}>(),
	{ card: true },
)

const shown = useChartView(props.chart)
shown.load()
</script>

<template>
	<ChartView :chart="shown" v-slot="{ chart, onSegmentClick }">
		<!-- No `title`: the host shows its own. No `filtered`: nothing here holds
		     filter state, so an empty chart has nothing to reset -->
		<ChartBody :chart="chart" :card="card" readonly @segment-click="onSegmentClick" />
	</ChartView>
</template>
