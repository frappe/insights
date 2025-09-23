<script setup lang="ts">
import { TextEditor, TextEditorFixedMenu } from 'frappe-ui'
import { inject, ref, unref } from 'vue'
import { WorkbookDashboardText } from '../types/workbook.types'
import { Dashboard } from './dashboard'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardText }>()

const editedText = ref(unref(props.item.text))
</script>

<template>
	<div class="prose w-full text-gray-700 h-full flex items-center">
		<div v-html="props.item.text"></div>
	</div>

	<!-- <Dialog
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
	> -->
<template 
v-if="dashboard.isEditingItem(props.item)"
		:modelValue="dashboard.isEditingItem(props.item)"
		@update:modelValue="!$event ? (dashboard.editingItemIndex = null) : true"
>
			<div class="space-y-2" 
			
			>
				<span class="block text-sm leading-4 text-gray-700">Content</span>
				<TextEditor
					ref="textEditor"
					:editable="true"
					:content="editedText"
					editor-class="min-h-[8rem] h-auto prose-sm cursor-text bg-gray-100 rounded p-2"
					@change="editedText = $event"
					placeholder="Enter your text content here..."
					>
				<template #bottom>
					<div class="mt-2 flex flex-col justify-between sm:flex-row sm:items-center">
        <TextEditorFixedMenu
          class="-ml-1 overflow-x-auto"
          :buttons="[
            'Paragraph',
            ['Heading 2', 'Heading 3', 'Heading 4'],
            'Separator',
            'Bold',
            'Italic',
            'Separator',
            'Bullet List',
            'Numbered List',
            'Separator',
            'Link',
            'Image',
          ]"
		  />
		  </div>
				</template>
				</TextEditor>
			</div>
		</template>
	<!-- </Dialog> -->
</template>
