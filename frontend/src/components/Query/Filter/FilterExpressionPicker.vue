<template>
	<div class="relative flex flex-col space-y-3">
		<!-- Expression Code Field -->
		<div class="mb-1 text-sm font-light">Expression</div>
		<div class="h-40 w-full text-sm">
			<Code
				v-model="input.value"
				:completions="getCompletions"
				@viewUpdate="codeViewUpdate"
			></Code>
		</div>
		<!-- Function Help -->
		<div
			v-if="expression.help?.syntax"
			class="absolute -left-[20.5rem] top-[22px] w-[20rem] rounded-md border bg-white p-2 shadow-lg"
		>
			<span class="mr-1 font-light">Syntax:</span>
			<span class="font-medium italic" style="font-family: 'Fira Code'">
				{{ expression.help.syntax }}
			</span>
			<br />
			<br />
			<span>{{ expression.help.description }}</span>
			<br />
			<br />
			<span class="mr-1 font-light">Example:</span>
			<span class="font-medium" style="font-family: 'Fira Code'">
				{{ expression.help.example }}
			</span>
		</div>
		<!-- Expression Error -->
		<div
			v-if="expression.error"
			class="!mt-1 flex items-center space-x-1 text-xs font-light text-red-500"
		>
			<FeatherIcon name="alert-circle" class="mr-1 h-3 w-3" />
			{{ expression.error }}
		</div>
		<!-- Action Buttons -->
		<div class="flex justify-end space-x-2">
			<Button
				appearance="primary"
				@click="addExpressionFilter"
				:disabled="Boolean(expression.error)"
			>
				{{ editing ? 'Update' : 'Add ' }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import Code from '@/components/Controls/Code.vue'
import { debounce } from 'frappe-ui'

import { FUNCTIONS } from '@/utils/query'
import { parse } from '@/utils/expressions'
import { inject, watchEffect, reactive } from 'vue'

const query = inject('query')

const emit = defineEmits(['filter-select', 'close'])
const props = defineProps({
	filter: {
		type: Object,
		default: {},
	},
})
const editing = false
const input = reactive({
	value: '',
	caretPosition: 0,
})

// parse the expression when input changes
const expression = reactive({
	raw: input.value,
	ast: null,
	error: null,
	tokens: [],
	help: null,
})
watchEffect(() => {
	expression.raw = input.value
	const { ast, tokens, errorMessage } = parse(expression.raw)
	expression.ast = ast
	expression.tokens = tokens
	expression.error = errorMessage
})

const getCompletions = (context, syntaxTree) => {
	let word = context.matchBefore(/\w*/)
	let nodeBefore = syntaxTree.resolveInner(context.pos, -1)

	if (nodeBefore.name === 'TemplateString') {
		return {
			from: word.from,
			options: query.columns.options.map((c) => {
				return { label: `${c.table}.${c.column}` }
			}),
		}
	}
	if (nodeBefore.name === 'VariableName') {
		return {
			from: word.from,
			options: Object.keys(FUNCTIONS).map((label) => ({ label })),
		}
	}
}

const codeViewUpdate = debounce(function ({ cursorPos }) {
	expression.help = null

	const { tokens } = expression
	const token = tokens.find((t) => t.start <= cursorPos && t.end >= cursorPos)
	if (token) {
		const { type, value } = token
		if (type == 'FUNCTION' && FUNCTIONS[value]) {
			expression.help = FUNCTIONS[value]
		}
	}
}, 300)

const addExpressionFilter = () => {
	emit('filter-select', expression.ast)
}
</script>
