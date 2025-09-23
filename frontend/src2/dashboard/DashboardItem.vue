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
import { TextEditor } from 'frappe-ui'

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

			<!-- <DashboardText
				v-else-if="props.item.type === 'text'"
				:item="(props.item as WorkbookDashboardText)"
			/> -->

			<TextEditor
			v-else-if="props.item.type === 'text'"
			:item="(props.item as WorkbookDashboardText)"
			<div class="p-2">
  <TextEditor
    editor-class="prose-sm min-h-[4rem] border rounded-b-lg border-t-0 p-2"
    :content="'<p></p>'"
    placeholder="Type something..."
    @change="(val) => value = val"
    :bubbleMenu="true"
    :fixed-menu="true"
  />

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
