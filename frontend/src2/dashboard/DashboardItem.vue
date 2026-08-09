<script setup lang="ts">
import { computed, inject } from 'vue'
import {
	WorkbookDashboardChart,
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
	WorkbookDashboardText,
} from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardChart from './DashboardChart.vue'
import DashboardFilter from './DashboardFilter.vue'
import DashboardItemActions from './DashboardItemActions.vue'
import DashboardText from './DashboardText.vue'
import type { DashboardCellProps, ViewerFilterState } from './viewer'

// One cell of a dashboard grid, as its author gets it: the same card a reader
// sees, drawn from the config being edited, with the affordances to change it.
//
// `filters` and `priority` are the page's answers for a reader, and this cell
// has better ones: the document it is editing carries the links that route a
// filter, which is what a reader is never given, and the store ranks the cards
// off the same document. So filter state is reported to the store, not up to the
// page — `filter` is declared to say it is answered here.
const props = defineProps<DashboardCellProps>()

defineEmits<{ loaded: [executedAt: Date]; resetFilters: []; filter: [state?: ViewerFilterState] }>()

// the live document item, which is what the editors below write to. The page
// hands it over as a viewer would read it, because that is the one shape both
// feeds answer with.
const item = computed(() => props.item as unknown as WorkbookDashboardItem)

const dashboard = inject('dashboard') as Dashboard
</script>

<template>
	<div class="group relative flex h-full w-full p-2">
		<div
			class="flex h-full w-full items-center justify-start"
			:class="
				dashboard.editing
					? 'pointer-events-none  [&>div:first-child]:rounded [&>div:first-child]:group-hover:outline [&>div:first-child]:group-hover:outline-gray-400'
					: ''
			"
		>
			<DashboardChart
				v-if="item.type == 'chart'"
				:item="item as WorkbookDashboardChart"
				:refresh-token="props.refreshToken"
				@loaded="$emit('loaded', $event)"
			/>

			<DashboardText v-else-if="item.type === 'text'" :item="item as WorkbookDashboardText" />

			<DashboardFilter
				v-else-if="item.type === 'filter'"
				:item="item as WorkbookDashboardFilter"
			/>
		</div>
		<DashboardItemActions
			v-if="dashboard.editing"
			class="absolute top-0 right-0 opacity-0 group-hover:opacity-100"
			:item-index="props.index"
		/>
	</div>
</template>
