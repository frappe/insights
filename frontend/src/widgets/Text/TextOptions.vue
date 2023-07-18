<script setup>
import { TextEditor } from 'frappe-ui'
import { computed } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
})

const options = computed({
	get() {
		return props.modelValue
	},
	set(value) {
		emit('update:modelValue', value)
	},
})
</script>

<template>
	<div class="space-y-2">
		<span class="block text-sm leading-4 text-gray-700">Content</span>
		<TextEditor
			ref="textEditor"
			:editable="true"
			:content="options.markdown"
			editor-class="h-[8rem] prose-sm cursor-text bg-gray-100 rounded p-2"
			@change="(val) => (options.markdown = val)"
		/>
	</div>
</template>
