<template>
	<div class="flex flex-col">
		<div class="mb-1 text-sm font-light text-gray-600">Expression</div>
		<Popover class="flex w-full [&>div:first-child]:w-full">
			<template #target="{ togglePopover }">
				<div class="relative font-mono">
					<input
						type="text"
						autocomplete="off"
						spellcheck="false"
						ref="inputElement"
						v-model="input.value"
						placeholder="Enter an expression..."
						@focus="togglePopover()"
						@keydown.esc.exact="togglePopover()"
						@keyup="input.caretPosition = $refs.inputElement.selectionStart"
						class="form-input block h-8 w-full select-none rounded-md border border-transparent p-0 pl-5 text-sm placeholder-gray-500 caret-black focus:border-transparent"
						:class="{
							'border border-red-500 focus:border-red-500': Boolean(expression.error),
						}"
					/>
					<div class="absolute top-0 left-0 flex h-8 items-center pl-2 text-gray-700">
						=
					</div>
					<div
						v-if="Boolean(expression.error)"
						class="absolute top-0 right-0 flex h-8 items-center pr-2 text-gray-700"
					>
						<FeatherIcon name="alert-circle" class="h-4 w-4 text-red-500" />
					</div>
				</div>
				<!-- <div class="mt-2 rounded-md border bg-slate-50 p-2">
					<pre>
						<code>
							{{ JSON.stringify(expression.tree, null, 2) }}
						</code>
					</pre>
				</div> -->
			</template>
			<template #body>
				<SuggestionBox
					v-if="showColumnDropdown && filteredColumns?.length"
					:header_and_suggestions="filteredColumns"
					@option-select="onColumnSelect"
				/>
			</template>
		</Popover>
		<div class="mt-2 text-sm text-gray-600">
			<div class="mb-1 font-light">Label</div>
			<Input
				type="text"
				v-model="expression.label"
				class="h-8 placeholder:text-sm"
				placeholder="Enter a label..."
			/>
		</div>
		<div class="mt-3 flex justify-end">
			<Button
				appearance="primary"
				@click="addExpressionColumn"
				:disabled="Boolean(expression.error)"
			>
				Add
			</Button>
		</div>
	</div>
</template>

<script setup>
import SuggestionBox from '@/components/SuggestionBox.vue'

import { parse } from '@/utils/expressions'
import { ref, inject, onMounted, watchEffect, reactive, computed } from 'vue'
import { autocompleteSquareBrackets, autocompleteQuotes } from '@/utils/autocomplete'

const query = inject('query')
const inputElement = ref(null)
const input = reactive({
	value: '',
	caretPosition: 0,
})

onMounted(() => {
	query.fetchColumns()
	autocompleteSquareBrackets(inputElement.value, input)
	autocompleteQuotes(inputElement.value, input)
})

// parse the expression when input changes
const expression = reactive({
	raw: '',
	label: '',
	tree: null,
	error: null,
	tokens: [],
})
watchEffect(() => {
	expression.raw = input.value
	try {
		const { parsed, tokens } = parse(expression.raw)
		expression.error = null
		expression.tree = parsed
		expression.tokens = tokens
	} catch (error) {
		console.warn(error.message)
		expression.tree = null
		expression.tokens = []
		expression.error = error.message
	}
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
		return query.fetchColumnsData.value
	}
	return query.fetchColumnsData.value?.filter(
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

const emit = defineEmits(['column-select'])
const addExpressionColumn = () => {
	const newColumn = {
		is_expression: 1,
		expression: {
			raw: expression.raw,
			tree: expression.tree,
		},
		label: expression.label,
	}
	emit('column-select', newColumn)
}
</script>
