<script setup lang="ts">
import { TextEditor } from 'frappe-ui'
import { inject, ref, unref } from 'vue'
import { WorkbookDashboardText } from '../types/workbook.types'
import { Dashboard } from './dashboard'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardText }>()

const editedText = ref(unref(props.item.text))
</script>

<template>
	<div v-html="props.item.text" class="prose w-full text-gray-700"></div>

	<Dialog
		v-if="dashboard.isEditingItem(props.item)"
		:modelValue="dashboard.isEditingItem(props.item)"
		@update:modelValue="!$event ? (dashboard.editingItemIndex = null) : true"
		:options="{
			title: 'Edit Text',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					disabled:
						!editedText || editedText.trim() === '' || editedText === props.item.text,
					onClick: () => {
						props.item.text = editedText
						dashboard.editingItemIndex = null
					},
				},
				{
					label: 'Cancel',
					onClick: () => (dashboard.editingItemIndex = null),
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
					:content="editedText"
					editor-class="min-h-[8rem] h-auto prose-sm cursor-text bg-gray-100 rounded p-2"
					@change="editedText = $event"
					placeholder="Enter your text content here..."
				/>
				<p class="text-xs text-gray-500">Markdown supported</p>
			</div>
		</template>
	</Dialog>
</template>
