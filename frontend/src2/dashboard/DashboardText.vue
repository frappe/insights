<script setup lang="ts">
import { Editor, EditorContent, RichTextKit } from 'frappe-ui/editor'
import { inject, ref, unref } from 'vue'
import { WorkbookDashboardText } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import { __ } from '../translation'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardText }>()

const editedText = ref(unref(props.item.text))
</script>

<template>
	<div class="prose max-w-none w-full text-gray-700 h-full flex items-center">
		<div v-html="props.item.text"></div>
	</div>

	<Dialog
		v-if="dashboard.isEditingItem(props.item)"
		:open="dashboard.isEditingItem(props.item)"
		@update:open="!$event ? (dashboard.editingItemIndex = undefined) : true"
		:title="__('Edit Text')"
		:actions="[
			{
				label: __('Save'),
				variant: 'solid',
				disabled: !editedText || editedText.trim() === '' || editedText === props.item.text,
				onClick: () => {
					props.item.text = editedText
					dashboard.editingItemIndex = undefined
				},
			},
			{
				label: __('Cancel'),
				onClick: () => (dashboard.editingItemIndex = undefined),
			},
		]"
	>
		<template #default>
			<div class="space-y-2">
				<span class="block text-sm leading-4 text-gray-700">{{ __('Content') }}</span>
				<Editor
					v-model="editedText"
					:extensions="[RichTextKit]"
					:placeholder="__('Enter your text content here...')"
				>
					<template #default="{ editor }">
						<EditorContent
							:editor="editor"
							class="min-h-[8rem] h-auto prose-sm cursor-text bg-gray-100 rounded p-2"
						/>
					</template>
				</Editor>
				<p class="text-xs text-gray-500">{{ __('Markdown supported') }}</p>
			</div>
		</template>
	</Dialog>
</template>
