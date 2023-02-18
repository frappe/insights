<script setup>
import { TextEditor } from 'frappe-ui'
import { ref, inject, watch, nextTick } from 'vue'
const props = defineProps({
	item_id: { required: true },
	options: { type: Object, required: true },
})

const dashboard = inject('dashboard')
const markdown = ref({ ...props.item }.markdown)

const textEditor = ref(null)
const editMarkdown = ref(false)
watch(editMarkdown, (value) => {
	value &&
		setTimeout(() => {
			textEditor.value.editor.commands.focus()
		}, 0)
})

function updateMarkdown() {
	dashboard.update_markdown
		.submit({
			item: { ...props.item, markdown: markdown.value },
		})
		.then(() => {
			editMarkdown.value = false
		})
}
async function discardText() {
	markdown.value = props.item.markdown
	// need to wait, for some reason, if not, then the text editor content is not updated
	await nextTick()
	editMarkdown.value = false
}
</script>

<template>
	<div class="relative flex h-full w-full items-center px-2">
		<TextEditor
			editor-class="h-fit prose-sm flex flex-col justify-end"
			:content="options.markdown"
			:editable="false"
		/>
	</div>
</template>

<style lang="scss">
.prose-sm {
	& > h1,
	& > h2,
	& > h3,
	& > h4,
	& > h5,
	& > h6 {
		@apply my-1;
	}
}
</style>
