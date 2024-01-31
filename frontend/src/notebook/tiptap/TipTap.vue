<template>
	<TextEditor
		ref="tiptap"
		editorClass="max-w-full custom-prose"
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
