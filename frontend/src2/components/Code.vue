<template>
	<p v-if="props.hideLineNumbers" class="font-mono text-gray-600 pl-2">=</p>
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
		:class="$attrs.class"
	/>
</template>

<script setup>
import { autocompletion, closeBrackets } from '@codemirror/autocomplete'
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { MySQL, sql } from '@codemirror/lang-sql'
import { syntaxTree } from '@codemirror/language'
import { linter } from '@codemirror/lint'
import { Decoration, EditorView, ViewPlugin } from '@codemirror/view'
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
	multiLine: {
		type: Boolean,
		default: true,
	},
	columnNames: {
		type: Array,
		default: () => [],
	},
	validationErrors: {
		type: Array,
		default: () => [],
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

const columnHighlighter = ViewPlugin.fromClass(
	class {
		decorations

		constructor(view) {
			this.decorations = this.buildDecorations(view)
		}

		update(update) {
			if (update.docChanged || update.viewportChanged) {
				this.decorations = this.buildDecorations(update.view)
			}
		}

		buildDecorations(view) {
			if (!props.columnNames || props.columnNames.length === 0) {
				return Decoration.none
			}

			const decorations = []
			const columnSet = new Set(props.columnNames)
			const doc = view.state.doc

			for (let i = 1; i <= doc.lines; i++) {
				const line = doc.line(i)
				const text = line.text

				// match only whole words ie `signups` but not `signups_today`
				const wordRegex = /\b\w+\b/g
				let match

				while ((match = wordRegex.exec(text)) !== null) {
					const word = match[0]
					if (columnSet.has(word)) {
						const from = line.from + match.index
						const to = from + word.length
						decorations.push(
							Decoration.mark({
								class: 'cm-column-highlight',
							}).range(from, to)
						)
					}
				}
			}

			return Decoration.set(decorations)
		}
	},
	{
		decorations: (v) => v.decorations,
	}
)

const validationLinter = linter((view) => {
	const diagnostics = []

	for (const error of props.validationErrors) {
		if (!error.line) continue
			const line = view.state.doc.line(error.line)
			const from = error.column ? line.from + error.column - 1 : line.from
			const to = error.column ? from + 1 : line.to

			diagnostics.push({
				from: Math.max(0, from),
				to: Math.min(view.state.doc.length, to),
				severity: 'error',
				message: error.message + (error.hint ? `\n${error.hint}` : ''),
			})
	}
	return diagnostics
})

const extensions = [language, closeBrackets(),tomorrow, validationLinter]

if (props.multiLine) {
	extensions.push(EditorView.lineWrapping)
}

if (props.columnNames && props.columnNames.length > 0) {
	extensions.push(columnHighlighter)
}

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
	insertText: (text) => {
		const view = codeMirror.value.view
		const pos = view.state.selection.ranges[0].to
		view.dispatch({
			changes: { from: pos, insert: text },
			selection: { anchor: pos + text.length, head: pos + text.length },
		})
		view.focus()
	},
})
</script>


