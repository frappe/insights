<template>
	<div class="flex flex-col space-y-3">
		<!-- Expression Field -->
		<Popover class="flex w-full flex-col [&>div:first-child]:w-full">
			<template #target="{ togglePopover }">
				<div class="mb-1 text-sm font-light text-gray-600">Expression</div>
				<div class="relative">
					<textarea
						rows="5"
						autocomplete="off"
						spellcheck="false"
						ref="inputElement"
						v-model="input.value"
						placeholder="Enter an expression..."
						@focus="togglePopover()"
						@keydown.esc.exact="togglePopover()"
						@keyup="input.caretPosition = $refs.inputElement.selectionStart"
						class="form-input w-full select-none rounded-md border border-transparent p-2 pl-5 font-mono text-sm placeholder-gray-500 caret-black focus:border-transparent"
						:class="{
							'border border-red-500 focus:border-red-500': Boolean(expression.error),
						}"
					/>
					<div class="absolute top-0 left-0 p-2 pt-2.5 font-mono">=</div>
				</div>
			</template>
			<template #body>
				<SuggestionBox
					v-show="showColumnDropdown && filteredColumns?.length"
					:suggestions="filteredColumns"
					@option-select="onColumnSelect"
				/>
			</template>
		</Popover>
		<!-- Expression Error -->
		<div
			v-if="expression.error"
			class="!mt-1 flex items-center space-x-1 text-xs font-light text-red-500"
		>
			<FeatherIcon name="alert-circle" class="mr-1 h-3 w-3" />
			{{ expression.error }}
		</div>
		<!-- Label Field -->
		<div class="text-sm text-gray-600">
			<div class="mb-1 font-light">Label</div>
			<Input
				type="text"
				v-model="expression.label"
				class="h-8 placeholder:text-sm"
				placeholder="Enter a label..."
			/>
		</div>
		<!-- Action Buttons -->
		<div class="flex justify-end space-x-2">
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
import SuggestionBox from '@/components/SuggestionBox.vue'

import { safeJSONParse } from '@/utils'
import { parse } from '@/utils/expressions'
import { ref, inject, onMounted, watchEffect, reactive, computed } from 'vue'
import { autocompleteSquareBrackets, autocompleteQuotes } from '@/utils/autocomplete'

const query = inject('query')
const inputElement = ref(null)

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
	expression: safeJSONParse(props.column.expression, {}),
}
const editing = ref(Boolean(column.name))
const input = reactive({
	value: column.expression.raw || '',
	caretPosition: column.expression.raw?.length || 0,
})

onMounted(() => {
	autocompleteSquareBrackets(inputElement.value, input)
	autocompleteQuotes(inputElement.value, input)
})

// parse the expression when input changes
const expression = reactive({
	raw: input.value,
	label: column.label,
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

// show column dropdown if the caret is between two square brackets
const showColumnDropdown = ref(false)
const columnTokenToEdit = ref(null)
watchEffect(() => {
	if (!expression.tokens || !expression.tokens.length) {
		showColumnDropdown.value = false
		columnTokenToEdit.value = null
		return
	}
	const columnToken = expression.tokens.find(
		(token) =>
			token.type === 'COLUMN' &&
			token.start <= input.caretPosition &&
			token.end >= input.caretPosition
	)
	showColumnDropdown.value = Boolean(columnToken)
	columnTokenToEdit.value = columnToken
})

const filteredColumns = computed(() => {
	if (!showColumnDropdown.value) {
		return []
	}

	const string = columnTokenToEdit.value?.value?.column?.toLowerCase()
	if (string && string.length === 0) {
		return query.columns.options
	}
	return query.columns.options?.filter(
		(column) =>
			column.label.toLowerCase().indexOf(string) > -1 ||
			column.column.toLowerCase().indexOf(string) > -1
	)
})

const onColumnSelect = (option) => {
	const stringBeforeColumn = input.value.slice(0, columnTokenToEdit.value.start - 1)
	const stringAfterColumn = input.value.slice(columnTokenToEdit.value.end + 1)

	const columnValue = `${option.table}.${option.column}`
	input.value = stringBeforeColumn + `[${columnValue}]` + stringAfterColumn

	inputElement.value.setSelectionRange(
		columnTokenToEdit.value.end + 1,
		columnTokenToEdit.value.end + 1
	)
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
	}
	emit('column-select', newColumn)
}

const removeExpressionColumn = () => {
	query.removeColumn.submit({ column: props.column })
	emit('close')
}
</script>
