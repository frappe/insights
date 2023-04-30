<template>
	<TextEditor
		ref="editor"
		:content="$props.content"
		editorClass="text-base max-w-full prose-h1:font-semibold prose-h1:my-5 prose-h2:font-semibold prose-h2:my-4 prose-p:text-lg prose-code:before:content-[''] prose-code:after:content-['']"
		@change="$emit('update:content', $event)"
		:starterkit-options="{ heading: { levels: [1, 2, 3] } }"
		:bubble-menu="[
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
		]"
		:placeholder="placeholderByNode"
		:extensions="[SlashCommand.configure({ suggestion }), QueryExtension]"
	></TextEditor>
</template>

<script setup>
import { TextEditor } from 'frappe-ui'
import { Code, RemoveFormatting, Strikethrough } from 'lucide-vue-next'
import QueryExtension from './extensions/query/QueryExtension'
import SlashCommand from './slash-command/commands'
import suggestion from './slash-command/suggestion'

function placeholderByNode({ node }) {
	if (node.type.name === 'heading') {
		return `Heading ${node.attrs.level}`
	}
	return 'Type / to insert a block'
}
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
</style>
