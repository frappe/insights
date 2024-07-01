<script setup lang="ts">
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { WorkbookDashboardChart, WorkbookDashboardItem } from '../types/workbook.types'
import { Workbook, workbookKey } from '../workbook/workbook'
import { Dashboard } from './dashboard'

const props = defineProps<{
	dashboard: Dashboard
	itemIndex: number
	item: WorkbookDashboardItem
}>()

const workbook = inject(workbookKey) as Workbook
const router = useRouter()

const chartIndex = computed(() => {
	if (props.item.type !== 'chart') return
	const chartItem = props.item as WorkbookDashboardChart
	return workbook.doc.charts.findIndex((c) => c.name === chartItem.chart)
})

const actions = [
	{
		icon: 'trash',
		label: 'Delete',
		onClick: () => props.dashboard.removeItem(props.itemIndex),
	},
]
if (props.item.type === 'chart') {
	actions.splice(0, 0, {
		icon: 'edit',
		label: 'Edit',
		onClick: () => router.push(`/workbook/${workbook.doc.name}/chart/${chartIndex.value}`),
	})
}
</script>
<template>
	<div class="flex w-fit cursor-pointer rounded bg-gray-800 p-1 shadow-sm">
		<div
			v-for="action in actions"
			:key="action.label"
			class="px-1 py-0.5"
			@click="action.onClick()"
		>
			<FeatherIcon :name="action.icon" class="h-3.5 w-3.5 text-white" />
		</div>
	</div>
</template>
