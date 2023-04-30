<template>
	<TextEditor
		:content="$props.content"
		editorClass="text-base prose-h1:font-semibold prose-h1:my-5 prose-h2:font-semibold prose-h2:my-4 prose-p:text-lg"
		@change="$emit('update:content', $event)"
		:starterkit-options="{ heading: { levels: [1, 2, 3] } }"
		:placeholder="placeholderByNode"
		:extensions="[SlashCommand.configure({ suggestion }), QueryExtension]"
	></TextEditor>
</template>

<script setup>
import { TextEditor } from 'frappe-ui'
import QueryExtension from './extensions/query/QueryExtension'
import SlashCommand from './slash-command/commands'
import suggestion from './slash-command/suggestion'

function placeholderByNode({ node }) {
	if (node.type.name === 'heading') {
		return `Heading ${node.attrs.level}`
	}
	return 'Type / to insert a command'
}
</script>

<style lang="scss">
/* Placeholder */
[data-placeholder].is-empty::before {
	content: attr(data-placeholder);
	float: left;
	pointer-events: none;
	height: 0;
	align-self: center;
	font-size: inherit;
	@apply absolute text-gray-300;
}
</style>
