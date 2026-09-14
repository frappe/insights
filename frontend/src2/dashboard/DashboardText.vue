<script setup lang="ts">
import DOMPurify from 'dompurify'
import { Editor, EditorContent, RichTextKit } from 'frappe-ui/editor'
import { computed, inject, ref, unref } from 'vue'
import { WorkbookDashboardText } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import { __ } from '../translation'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardText }>()

const editedText = ref(unref(props.item.text))

// The card is authored as rich text and drawn as HTML, and a public link draws
// it to a reader with no session. The dashboard sanitizes a text item on the way
// in, so this is the second half of the same rule: an item a patch wrote, or one
// stored before that rule existed, still reaches the DOM through here.
const textHtml = computed(() => (props.item.text ? DOMPurify.sanitize(props.item.text) : ''))
</script>

<template>
	<!-- centered with `my-auto` on the content rather than `justify-center` on the
	     box: a centered flex column scrolls away from text taller than the cell,
	     and the top of it can never be reached -->
	<div v-if="props.item.text" class="flex h-full w-full flex-col overflow-auto">
		<div class="prose prose-v3 my-auto max-w-none text-ink-gray-7" v-html="textHtml"></div>
	</div>
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
							class="h-auto min-h-[8rem] cursor-text rounded-4 bg-surface-gray-2 p-2"
						/>
					</template>
				</Editor>
				<p class="text-xs text-ink-gray-5">{{ __('Markdown supported') }}</p>
			</div>
		</template>
	</Dialog>
</template>
