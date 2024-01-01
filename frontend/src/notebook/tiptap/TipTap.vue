<template>
	<TextEditor
		ref="tiptap"
		editorClass="max-w-full prose-h1:font-semibold prose-h1:mt-5 prose-h1:mb-3 prose-h2:font-semibold prose-h2:mt-4 prose-h2:mb-2 prose-p:!my-0 prose-p:py-1 prose-p:text-[16px] prose-p:leading-6 prose-code:before:content-[''] prose-code:after:content-[''] prose-ul:my-0 prose-ol:my-0 prose-li:my-0 prose-th:py-1 prose-td:py-1 prose-blockquote:my-3"
		@change="updateContent"
		:bubble-menu="bubbleMenu"
		:bubble-menu-options="{
			shouldShow: (opts) => {
				// Don't show when the selection is empty
				if (opts.from === opts.to) return false
				return !opts.editor.isActive('query-editor') && !opts.editor.isActive('chart')
			},
		}"
		:placeholder="placeholderByNode"
		:extensions="[SlashCommand.configure({ suggestion }), QueryEditor, Chart]"
	></TextEditor>
</template>

<script setup>
import { safeJSONParse } from '@/utils'
import { TextEditor } from 'frappe-ui'
import { Code, RemoveFormatting, Strikethrough } from 'lucide-vue-next'
import { onMounted, ref, watch } from 'vue'
import Chart from './extensions/Chart'
import QueryEditor from './extensions/QueryEditor'
import SlashCommand from './slash-command/commands'
import suggestion from './slash-command/suggestion'

const emit = defineEmits(['update:content'])
const props = defineProps(['content'])

const tiptap = ref(null)
const updateContent = () => {
	const contentJSON = tiptap.value.editor.getJSON()
	emit('update:content', contentJSON)
}

onMounted(() => {
	const content = safeJSONParse(props.content)
	tiptap.value.editor.commands.setContent(content)
})
watch(
	() => props.content,
	(newContent) => {
		const _newContent = safeJSONParse(newContent)
		if (!_newContent) return
		const editorContent = tiptap.value.editor.getJSON()
		if (JSON.stringify(_newContent) !== JSON.stringify(editorContent)) {
			tiptap.value.editor.commands.setContent(_newContent)
		}
	}
)

function placeholderByNode({ node }) {
	if (node.type.name === 'heading') {
		return `Heading ${node.attrs.level}`
	}
	return 'Type / to insert a block'
}

const bubbleMenu = [
	'Bold',
	'Italic',
	{
		label: 'Strikethrough',
		icon: Strikethrough,
		action: (editor) => editor.chain().focus().toggleStrike().run(),
		isActive: (editor) => editor.isActive('strike'),
	},
	'Blockquote',
	{
		label: 'Code',
		icon: Code,
		action: (editor) => editor.chain().focus().toggleCode().run(),
		isActive: (editor) => editor.isActive('code'),
	},
	'Link',
	{
		label: 'Remove Formatting',
		icon: RemoveFormatting,
		action: (editor) => editor.chain().focus().unsetAllMarks().run(),
		isActive: () => false,
	},
]
</script>

<style lang="scss">
/* Placeholder */
.prose [data-placeholder].is-empty::before {
	content: attr(data-placeholder);
	float: left;
	pointer-events: none;
	height: 0;
	align-self: center;
	font-size: inherit;
	@apply absolute text-gray-300;
}

.prose :where(blockquote p:first-of-type):not(:where([class~='not-prose'] *)) {
	&::before {
		content: '';
	}
	&::after {
		content: '';
	}
}

.prose :where(code):not(:where([class~='not-prose'] *)) {
	@apply rounded bg-gray-100 px-1.5 py-1 text-gray-700;
}

.prose :where(pre):not(:where([class~='not-prose'] *)) {
	@apply bg-gray-100 text-gray-800;
}

.prose table p {
	@apply text-base;
}

.ProseMirror:not(.ProseMirror-focused) p.is-editor-empty:first-child::before {
	@apply text-gray-500;
}
</style>
