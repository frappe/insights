<script setup lang="ts">
import type { WorkbookDashboardText } from '../types/workbook.types'
import DashboardChartView from './DashboardChartView.vue'
import DashboardFilter from './DashboardFilter.vue'
import DashboardText from './DashboardText.vue'
import type { DashboardCellProps } from './view'

// One cell of a dashboard grid, as a reader gets it. A chart card owns its own
// states, so a cell that cannot load leaves the page alone.
//
// A text item is drawn by the component that owns drawing one, the way a chart
// and a filter are: it is stored as HTML, and the cleaning on the way out lives
// where it is written to the DOM.
//
// A filter is a cell like any other, in the position its owner gave it. The one
// thing it cannot do here is name its own column — the link that says so never
// reaches a reader — so it asks the page for its values by filter name and lets
// the server route what it lands on.
const props = defineProps<DashboardCellProps>()
</script>

<template>
	<div class="flex h-full w-full justify-start p-2">
		<DashboardChartView
			v-if="props.item.type === 'chart'"
			:item="props.item"
			:dashboard="props.dashboard"
		/>
		<DashboardText
			v-else-if="props.item.type === 'text'"
			:item="props.item as unknown as WorkbookDashboardText"
		/>
		<DashboardFilter
			v-else-if="props.item.type === 'filter'"
			:item="props.item"
			:dashboard="props.dashboard"
		/>
	</div>
</template>
