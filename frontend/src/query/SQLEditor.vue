<template>
	<codemirror
		:tab-size="2"
		v-model="code"
		:autofocus="true"
		:indent-with-tab="true"
		:extensions="extensions"
		placeholder="Write your custom SQL query here..."
		@update="onUpdate"
	/>
</template>

<script setup>
import { computed, watch } from 'vue'
import { tags } from '@lezer/highlight'
import { Codemirror } from 'vue-codemirror'
import { EditorView } from '@codemirror/view'
import { sql } from '@codemirror/lang-sql'
import { autocompletion, closeBrackets } from '@codemirror/autocomplete'
import { HighlightStyle, syntaxHighlighting, syntaxTree } from '@codemirror/language'

const props = defineProps({
	modelValue: {
		required: true,
	},
	completions: {
		type: Function,
		default: null,
	},
})
const emit = defineEmits(['update:modelValue', 'inputChange', 'viewUpdate'])

const onUpdate = (viewUpdate) => {
	emit('viewUpdate', {
		cursorPos: viewUpdate.state.selection.ranges[0].to,
	})
}

const code = computed({
	get: () => props.modelValue || '',
	set: (value) => emit('update:modelValue', value),
})
watch(code, (value, oldValue) => {
	if (value !== oldValue) {
		emit('inputChange', value)
	}
})

const extensions = [sql(), closeBrackets(), EditorView.lineWrapping]
const autocompletionOptions = {
	activateOnTyping: true,
	closeOnBlur: false,
	maxRenderedOptions: 10,
	icons: false,
	optionClass: () => 'flex h-7 !px-2 items-center rounded-md !text-gray-600',
}
if (props.completions) {
	autocompletionOptions.override = [
		(context) => {
			return props.completions(context, syntaxTree(context.state))
		},
	]
}
extensions.push(autocompletion(autocompletionOptions))

const chalky = '#e5a05b',
	coral = '#b04a54',
	cyan = '#45a5b1',
	invalid = '#ffffff',
	ivory = '#6a6a6a',
	stone = '#7d8799', // Brightened compared to original to increase contrast
	malibu = '#61afef',
	sage = '#76c457',
	whiskey = '#d19a66',
	violet = '#c678dd'

const getHighlighterStyle = () =>
	HighlightStyle.define([
		{ tag: tags.keyword, color: violet },
		{
			tag: [tags.name, tags.deleted, tags.character, tags.propertyName, tags.macroName],
			color: coral,
		},
		{
			tag: [tags.function(tags.variableName), tags.labelName],
			color: malibu,
		},
		{
			tag: [tags.color, tags.constant(tags.name), tags.standard(tags.name)],
			color: whiskey,
		},
		{ tag: [tags.definition(tags.name), tags.separator], color: ivory },
		{
			tag: [
				tags.typeName,
				tags.className,
				tags.number,
				tags.changed,
				tags.annotation,
				tags.modifier,
				tags.self,
				tags.namespace,
			],
			color: chalky,
		},
		{
			tag: [
				tags.operator,
				tags.operatorKeyword,
				tags.url,
				tags.escape,
				tags.regexp,
				tags.link,
				tags.special(tags.string),
			],
			color: cyan,
		},
		{ tag: [tags.meta, tags.comment], color: stone },
		{ tag: tags.strong, fontWeight: 'bold' },
		{ tag: tags.emphasis, fontStyle: 'italic' },
		{ tag: tags.strikethrough, textDecoration: 'line-through' },
		{ tag: tags.link, color: stone, textDecoration: 'underline' },
		{ tag: tags.heading, fontWeight: 'bold', color: coral },
		{
			tag: [tags.atom, tags.bool, tags.special(tags.variableName)],
			color: whiskey,
		},
		{
			tag: [tags.processingInstruction, tags.string, tags.inserted],
			color: sage,
		},
		{ tag: tags.invalid, color: invalid },
	])

extensions.push(syntaxHighlighting(getHighlighterStyle()))
</script>
