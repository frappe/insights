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

// A grid cell in the builder: the card a reader sees, rendered from the config
// being edited, with the controls to change it.
//
// It edits through the store the builder provides. The store holds the whole
// document, not only what a reader gets.
const props = defineProps<DashboardCellProps>()

// The editors below write to the document item itself. The page passes it in
// the reader's shape, because both the view and the builder use that shape.
const item = computed(() => props.item as unknown as WorkbookDashboardItem)

const dashboard = inject('dashboard') as Dashboard
</script>

<template>
	<div class="group relative flex h-full w-full p-2">
		<!-- A card fills its cell. Nothing is centered in it: a Number cell is as
		     tall as its card, and every other type renders into the whole box. -->
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
