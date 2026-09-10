<script setup lang="ts">
import { computed, inject } from 'vue'
import {
	WorkbookDashboardFilter,
	WorkbookDashboardItem,
	WorkbookDashboardText,
} from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardChart from './DashboardChart.vue'
import DashboardFilter from './DashboardFilter.vue'
import DashboardFilterEditor from './DashboardFilterEditor.vue'
import DashboardItemActions from './DashboardItemActions.vue'
import DashboardText from './DashboardText.vue'
import type { DashboardCellProps } from './view'

// One cell of a dashboard grid, as its author gets it: the same card a reader
// sees, drawn from the config being edited, with the affordances to change it.
//
// It takes the page's own cell props, because the body passes the same ones to
// whichever cell it was mounted with. What it edits it reaches through the store
// the builder provides, which carries the whole document rather than what a
// reader is given of it.
const props = defineProps<DashboardCellProps>()

// the live document item, which is what the editors below write to. The page
// hands it over as a reader would read it, because that is the one shape both
// sources answer with.
const item = computed(() => props.item as unknown as WorkbookDashboardItem)

const dashboard = inject('dashboard') as Dashboard
</script>

<template>
	<div class="group relative flex h-full w-full p-2">
		<!-- A card fills its cell. Nothing is centered in it: a Number cell is as
		     tall as its card, and every other type draws into the whole box. -->
		<div
			class="flex h-full w-full justify-start"
			:class="
				dashboard.editing
					? 'pointer-events-none  [&>div:first-child]:rounded-4 [&>div:first-child]:group-hover:outline [&>div:first-child]:group-hover:outline-outline-gray-3'
					: ''
			"
		>
			<DashboardChart
				v-if="item.type == 'chart'"
				:item="props.item"
				:dashboard="props.dashboard"
			/>

			<DashboardText v-else-if="item.type === 'text'" :item="item as WorkbookDashboardText" />

			<DashboardFilter
				v-else-if="item.type === 'filter'"
				:item="props.item"
				:dashboard="props.dashboard"
			/>
		</div>
		<DashboardFilterEditor
			v-if="item.type === 'filter' && dashboard.isEditingItem(item)"
			:item="item as WorkbookDashboardFilter"
		/>
		<DashboardItemActions
			v-if="dashboard.editing"
			class="absolute top-0 right-0 opacity-0 group-hover:opacity-100"
			:item-index="props.index"
		/>
	</div>
</template>
