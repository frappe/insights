<script setup lang="ts">
import { TextEditor } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
	WorkbookDashboardChart,
	WorkbookDashboardItem,
	WorkbookDashboardText,
} from '../types/workbook.types'
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

const showTextWidgetEditDialog = ref(false)
const text = ref((props.item as WorkbookDashboardText).text)

if (props.item.type === 'text') {
	actions.splice(0, 0, {
		icon: 'edit',
		label: 'Edit',
		onClick: () => (showTextWidgetEditDialog.value = true),
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

	<Dialog
		v-model="showTextWidgetEditDialog"
		:options="{
			title: 'Edit Text',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					disabled: !text || text.trim() === '' || text === (props.item as WorkbookDashboardText).text,
					onClick: () => {
						(props.item as WorkbookDashboardText).text = text
						showTextWidgetEditDialog = false
					},
				},
				{
					label: 'Cancel',
					onClick: () => (showTextWidgetEditDialog = false),
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-2">
				<span class="block text-sm leading-4 text-gray-700">Content</span>
				<TextEditor
					ref="textEditor"
					:editable="true"
					:content="text"
					editor-class="h-[8rem] prose-sm cursor-text bg-gray-100 rounded p-2"
					@change="text = $event"
				/>
				<p class="text-xs text-gray-500">Markdown supported</p>
			</div>
		</template>
	</Dialog>
</template>
