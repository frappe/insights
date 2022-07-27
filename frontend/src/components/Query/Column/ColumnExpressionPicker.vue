<template>
	<div class="flex flex-col">
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
		<!-- Label Field -->
		<div class="mt-2 text-sm text-gray-600">
			<div class="mb-1 font-light">Label</div>
			<Input
				type="text"
				v-model="expression.label"
				class="h-8 placeholder:text-sm"
				placeholder="Enter a label..."
			/>
		</div>
		<div class="mt-4 text-sm text-gray-600">
			<Input type="checkbox" label="Group By" v-model="expression.groupBy" />
		</div>
		<!-- Action Buttons -->
		<div class="mt-3 flex justify-end space-x-2">
			<Button
				v-if="editing"
				class="text-red-500"
				appearance="white"
				@click="removeExpressionColumn"
			>
				Remove
			</Button>
			<Button
				appearance="primary"
				@click="addExpressionColumn"
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
import { ref, inject, watchEffect, reactive } from 'vue'

const $utils = inject('$utils')
const query = inject('query')

const emit = defineEmits(['column-select', 'close'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
		validate: (value) => {
			if (value.is_expression != 1) {
				return 'Column must be an expression'
			}
		},
	},
})

const column = {
	...props.column,
	expression: $utils.safeJSONParse(props.column.expression, {}),
}
const editing = ref(Boolean(column.name))
const input = reactive({
	value: column.expression.raw || '',
	caretPosition: column.expression.raw?.length || 0,
})

// parse the expression when input changes
const expression = reactive({
	raw: input.value,
	label: column.label,
	groupBy: column.aggregation == 'Group By',
	ast: null,
	error: null,
	tokens: [],
})
watchEffect(() => {
	expression.raw = input.value
	const { ast, tokens, errorMessage } = parse(input.value)
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

const addExpressionColumn = () => {
	const newColumn = {
		name: props.column.name,
		is_expression: 1,
		expression: {
			raw: expression.raw,
			ast: expression.ast,
		},
		label: expression.label,
		aggregation: expression.groupBy ? 'Group By' : '',
	}
	emit('column-select', newColumn)
}

const removeExpressionColumn = () => {
	query.removeColumn.submit({ column: props.column })
	emit('close')
}
</script>
