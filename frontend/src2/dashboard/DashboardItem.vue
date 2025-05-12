<script setup lang="ts">
import { inject } from 'vue'
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

const props = defineProps<{
	index: number
	item: WorkbookDashboardItem
}>()

const dashboard = inject('dashboard') as Dashboard
</script>

<template>
	<div class="group relative flex h-full w-full p-2">
		<div
			class="flex h-full w-full items-center justify-center"
			:class="
				dashboard.editing
					? 'pointer-events-none  [&>div:first-child]:rounded [&>div:first-child]:group-hover:outline [&>div:first-child]:group-hover:outline-gray-400'
					: ''
			"
		>
			<DashboardChart
				v-if="props.item.type == 'chart'"
				:item="(props.item as WorkbookDashboardChart)"
			/>

			<DashboardText
				v-else-if="props.item.type === 'text'"
				:item="(props.item as WorkbookDashboardText)"
			/>

			<DashboardFilter
				v-else-if="props.item.type === 'filter'"
				:item="(props.item as WorkbookDashboardFilter)"
			/>
		</div>
		<DashboardItemActions
			v-if="dashboard.editing"
			class="absolute top-0 right-0 opacity-0 group-hover:opacity-100"
			:item-index="index"
		/>
	</div>
</template>
