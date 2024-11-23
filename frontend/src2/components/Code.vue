<template>
	<codemirror
		:tab-size="2"
		:disabled="readOnly"
		v-model="code"
		class="font-[400]"
		:autofocus="autofocus"
		:indent-with-tab="true"
		:extensions="extensions"
		:placeholder="placeholder"
		@update="onUpdate"
		@focus="emit('focus')"
		@blur="emit('blur')"
		@ready="codeMirror = $event"
	/>
</template>

<script setup>
import { autocompletion, closeBrackets } from '@codemirror/autocomplete'
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { MySQL, sql } from '@codemirror/lang-sql'
import { syntaxTree } from '@codemirror/language'
import { EditorView } from '@codemirror/view'
import { onMounted, ref, watch } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { tomorrow } from 'thememirror'

const props = defineProps({
	modelValue: String,
	readOnly: {
		type: Boolean,
		default: false,
	},
	autofocus: {
		type: Boolean,
		default: true,
	},
	placeholder: {
		type: String,
		default: 'Enter an expression...',
	},
	completions: {
		type: Function,
		default: null,
	},
	language: {
		type: String,
		default: 'javascript',
	},
	tables: {
		type: Array,
		default: () => [],
	},
	schema: {
		type: Object,
		default: () => ({}),
	},
	hideLineNumbers: {
		type: Boolean,
		default: false,
	},
	disableAutocompletions: {
		type: Boolean,
		default: false,
	},
})
const emit = defineEmits(['inputChange', 'viewUpdate', 'focus', 'blur'])

onMounted(() => {
	if (props.hideLineNumbers) {
		document.querySelectorAll('.cm-gutters').forEach((gutter) => {
			gutter.style.display = 'none'
		})
	}
})

const onUpdate = (viewUpdate) => {
	emit('viewUpdate', {
		cursorPos: viewUpdate.state.selection.ranges[0].to,
		syntaxTree: syntaxTree(viewUpdate.state),
		state: viewUpdate.state,
	})
}

const codeMirror = ref(null)
const code = defineModel()
watch(code, (value, oldValue) => {
	if (value !== oldValue) {
		emit('inputChange', value)
	}
})

const language =
	props.language === 'javascript'
		? javascript()
		: props.language === 'python'
		? python()
		: sql({
				dialect: MySQL,
				upperCaseKeywords: true,
				schema: props.schema,
				tables: props.tables,
		  })

const extensions = [language, closeBrackets(), EditorView.lineWrapping, tomorrow]
const autocompletionOptions = {
	activateOnTyping: true,
	closeOnBlur: false,
	maxRenderedOptions: 10,
	icons: false,
	optionClass: () => 'flex h-7 !px-2 items-center rounded !text-gray-600',
}
if (props.completions) {
	autocompletionOptions.override = [
		(context) => {
			return props.completions(context, syntaxTree(context.state))
		},
	]
}
extensions.push(autocompletion(autocompletionOptions))

defineExpose({
	get cursorPos() {
		return codeMirror.value.view.state.selection.ranges[0].to
	},
	focus: () => codeMirror.value.view.focus(),
	setCursorPos: (pos) => {
		const _pos = Math.min(pos, code.value.length)
		codeMirror.value.view.dispatch({ selection: { anchor: _pos, head: _pos } })
	},
})
</script>
