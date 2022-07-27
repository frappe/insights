<template>
	<div class="flex flex-col space-y-3">
		<!-- Expression Code Field -->
		<div class="mb-1 text-sm font-light">Expression</div>
		<div class="h-40 w-full text-sm">
			<Code v-model="input.value" :completions="getCompletions"></Code>
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

const addExpressionFilter = () => {
	emit('filter-select', expression.ast)
}
</script>
