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
	<div
		v-if="props.item.text"
		class="prose prose-v3 h-full w-full max-w-none overflow-auto text-ink-gray-7"
		v-html="props.item.text"
	></div>
	<div
		v-else-if="dashboard.editing"
		class="flex h-full w-full items-center text-sm text-ink-gray-4"
	>
		{{ __('Empty text — click edit to add content') }}
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
				<span class="block text-sm leading-4 text-ink-gray-7">{{ __('Content') }}</span>
				<Editor
					v-model="editedText"
					:extensions="[RichTextKit]"
					:placeholder="__('Enter your text content here...')"
				>
					<template #default="{ editor }">
						<EditorContent
							:editor="editor"
							class="h-auto min-h-[8rem] cursor-text rounded bg-surface-gray-2 p-2"
						/>
					</template>
				</Editor>
				<p class="text-xs text-ink-gray-5">{{ __('Markdown supported') }}</p>
			</div>
		</template>
	</Dialog>
</template>
