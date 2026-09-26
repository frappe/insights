<script setup lang="ts">
import type { WorkbookDashboardText } from '../types/workbook.types'
import DashboardChartView from './DashboardChartView.vue'
import DashboardFilter from './DashboardFilter.vue'
import DashboardText from './DashboardText.vue'
import type { DashboardCellProps } from './view'

// A grid cell as a reader gets it. A chart card handles its own loading and
// error states, so a card that fails does not break the page.
//
// `DashboardText` renders a text item. It is stored as HTML, and that component
// sanitizes it where it writes it to the DOM.
//
// A reader never gets a filter's column. So the filter asks the page for its
// values by filter name, and the server applies it to the right column.
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
