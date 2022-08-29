<template>
	<div class="relative flex flex-col">
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
		<!-- Type Field -->
		<div class="mt-2 text-sm text-gray-600">
			<div class="mb-1 font-light">Type</div>
			<Input
				type="select"
				v-model="expression.valueType"
				class="h-8 placeholder:text-sm"
				placeholder="Select a type..."
				:options="Object.values(typeMap)"
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
			<Button appearance="primary" @click="addExpressionColumn" :disabled="addDisabled">
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
import { ref, inject, watchEffect, reactive, computed } from 'vue'

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
	expression: props.column.expression || {},
}
const editing = ref(Boolean(column.name))
const input = reactive({
	value: column.expression.raw || '',
	caretPosition: column.expression.raw?.length || 0,
})

const typeMap = {
	Time: 'Time',
	Date: 'Date',
	Varchar: 'String',
	Int: 'Integer',
	Float: 'Decimal',
	Datetime: 'Datetime',
	Timestamp: 'Timestamp',
}

// parse the expression when input changes
const expression = reactive({
	raw: input.value,
	label: column.label,
	groupBy: column.aggregation == 'Group By',
	valueType: typeMap[column.type] || 'String',
	ast: null,
	error: null,
	tokens: [],
	help: null,
})
watchEffect(() => {
	expression.raw = input.value
	const { ast, tokens, errorMessage } = parse(input.value)
	expression.ast = ast
	expression.tokens = tokens
	expression.error = errorMessage
})

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

const addDisabled = computed(() => {
	return Boolean(
		expression.error || !expression.raw || !expression.label || !expression.valueType
	)
})

const addExpressionColumn = () => {
	const type = Object.keys(typeMap).find((key) => typeMap[key] === expression.valueType)
	const newColumn = {
		name: props.column.name,
		is_expression: 1,
		expression: {
			raw: expression.raw,
			ast: expression.ast,
		},
		type: type,
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
