<template>
	<div class="flex flex-col">
		<div class="text-sm font-light text-gray-600">Expression</div>
		<div id="expression_filter_picker" class="relative z-10 mt-1 w-full rounded-md shadow-sm">
			<Popover class="flex w-full [&>div:first-child]:w-full">
				<template #target="{ isOpen, togglePopover }">
					<div class="relative">
						<input
							type="text"
							autocomplete="off"
							spellcheck="false"
							v-model="input"
							ref="filterInput"
							@focus="togglePopover()"
							@keydown.esc.exact="togglePopover()"
							class="form-input block h-8 w-full select-none rounded-md p-0 pl-5 tracking-widest placeholder-gray-500 caret-black"
							:class="{
								'focus:rounded-b-none focus:bg-white focus:shadow':
									isOpen && options?.length && filteredOptions?.length,
							}"
						/>
						<div class="absolute top-0 left-0 flex h-8 items-center pl-2 text-gray-700">=</div>
					</div>
				</template>
				<template #body="{ isOpen, togglePopover }">
					<SuggestionBox
						v-if="isOpen && options?.length && filteredOptions?.length"
						:header_and_suggestions="filteredOptions"
						@option-select="
							(option) => {
								onOptionSelect(option)
								togglePopover()
							}
						"
					/>
				</template>
			</Popover>
		</div>
		<div class="mt-2 rounded-md border border-orange-50 bg-orange-50/80 p-2 text-sm font-light text-gray-500">
			<ul class="list-disc pl-4">
				<li>
					You can select a column by typing
					<span class="font-medium tracking-widest"> [column] </span>
				</li>
				<li>
					You can use following operators:
					<ul class="pl-4" style="list-style-type: square">
						<li>Arithmetic: <span class="font-medium tracking-widest"> +, -, *, /</span></li>
						<li>
							Comparison:
							<span class="font-medium tracking-widest"
								>, =, !=, &lt;, &gt;, &lt;=, &gt;=, is, in, not in, between, contains, starts with, ends with, not
								contains
							</span>
						</li>
					</ul>
				</li>
			</ul>
		</div>
		<div class="mt-3 flex justify-end">
			<Button appearance="primary" @click="apply" :disabled="input.length == 0"> Apply </Button>
		</div>
	</div>
</template>

<script setup>
import SuggestionBox from '@/components/SuggestionBox.vue'
import { debounce } from 'frappe-ui'

import { inject, onMounted, nextTick, onBeforeUnmount, computed, ref, watch } from 'vue'

const arithmetic_operators = [' + ', ' - ', ' * ', ' / ']
const compare_operators = [
	' = ',
	' != ',
	' > ',
	' < ',
	' >= ',
	' <= ',
	' is ',
	' in ',
	' not in ',
	' between ',
	' contains ',
	' starts with ',
	' ends with ',
	' not contains ',
]

const query = inject('query')
const $notify = inject('$notify')

const emit = defineEmits(['filter-select'])
const props = defineProps({
	filter: {
		type: Object,
		default: {
			expression: '',
			left: {},
			operator: {},
			right: {},
		},
	},
})

const get_columns_from_filter = (filter) => {
	const columns = {}

	function find_columns(o) {
		if (o.column && o.table) {
			columns[o.label] = o
		}

		if (o.left && o.right && o.operator) {
			find_columns(o.left)
			find_columns(o.right)
		}
	}

	find_columns(filter)

	return columns
}

const showColumns = ref(false)
const caretPosition = ref(null)
const stringAroundCaret = ref('')

const input = ref(props.filter.expression || '')
const selectedColumns = ref(props.filter.expression ? get_columns_from_filter(props.filter) : {})

const filterInput = ref(null)

const input_keyup_listener = (e) => {
	caretPosition.value = e.target.selectionStart
	auto_add_close_square_brackets(e)
	auto_add_quotes(e)
}
const input_keydown_listener = (e) => {
	caretPosition.value = e.target.selectionStart
	auto_remove_close_square_bracket(e)
	auto_remove_quotes(e)
}
onMounted(() => {
	query.fetchColumns()
	filterInput.value?.addEventListener('keyup', input_keyup_listener)
	filterInput.value?.addEventListener('keydown', input_keydown_listener)
})
onBeforeUnmount(() => {
	filterInput.value?.removeEventListener('keyup', input_keyup_listener)
	filterInput.value?.removeEventListener('keydown', input_keydown_listener)
})

watch(input, (newInput) => {
	// if newInput doesn't contains selectedColumns keys, remove them
	for (let key of Object.keys(selectedColumns.value)) {
		if (!newInput.includes(`[${key}]`)) {
			delete selectedColumns.value[key]
		}
	}
})

watch(
	caretPosition,
	debounce(function (newCaretPosition) {
		// get string around caret between sqaure brackets
		const start_index = input.value.lastIndexOf('[', newCaretPosition)
		const end_index = input.value.indexOf(']', newCaretPosition)
		const _stringAroundCaret = input.value.slice(start_index + 1, end_index > 0 ? end_index : input.value.length)

		if (_stringAroundCaret.length && (!_stringAroundCaret.includes('[') || !_stringAroundCaret.includes(']'))) {
			showColumns.value = true
			stringAroundCaret.value = _stringAroundCaret
		} else {
			showColumns.value = false
			stringAroundCaret.value = ''
		}
	}, 200)
)

const columnOptions = computed(() => {
	return query.fetchColumnsData.value?.map((c) => {
		return {
			...c,
			value: c.column,
			secondary_label: c.table_label,
		}
	})
})
const options = computed(() => {
	return showColumns.value ? columnOptions.value : []
})
const filteredOptions = computed(() => {
	return stringAroundCaret.value
		? options.value.filter((o) => {
				return o.label.toLowerCase().includes(stringAroundCaret.value.toLowerCase())
		  })
		: options.value
})

function onOptionSelect(suggestion) {
	let start_index = input.value.lastIndexOf('[', caretPosition.value)
	let end_index = input.value.indexOf(']', caretPosition.value)
	end_index = end_index > 0 ? end_index : input.value.length

	const left_part = input.value.slice(0, start_index + 1)
	const right_part = input.value.slice(end_index)
	const newInput = left_part + `[${suggestion.label}]` + right_part
	input.value = newInput.replaceAll('[[', '[').replaceAll(']]', ']')

	selectedColumns.value[suggestion.label] = suggestion

	showColumns.value = false
	stringAroundCaret.value = ''

	filterInput.value?.focus()
}
function apply() {
	const filter = build_filter()
	if (filter) {
		emit('filter-select', { filter })
	}
}
function build_filter() {
	const filter = { is_expression: true, expression: input.value }
	filter.operator = get_compare_operator()

	if (!filter.operator) {
		return
	}

	const [left, right] = input.value.split(filter.operator.value)
	filter.left = build_filter_part(left)
	filter.right = build_filter_part(right)

	return filter
}
function build_filter_part(expression) {
	let filter_part = {}

	if (expression.includes('/')) {
		const [left, right] = expression.split('/')
		filter_part.left = build_filter_part(left.trim())
		filter_part.right = build_filter_part(right.trim())
		filter_part.operator = get_operator('/')
		return filter_part
	}
	if (expression.includes('*')) {
		const [left, right] = expression.split('*')
		filter_part.left = build_filter_part(left.trim())
		filter_part.right = build_filter_part(right.trim())
		filter_part.operator = get_operator('*')
		return filter_part
	}
	if (expression.includes('+')) {
		const [left, right] = expression.split('+')
		filter_part.left = build_filter_part(left.trim())
		filter_part.right = build_filter_part(right.trim())
		filter_part.operator = get_operator('+')
		return filter_part
	}
	if (expression.includes('-')) {
		const [left, right] = expression.split('-')
		filter_part.left = build_filter_part(left.trim())
		filter_part.right = build_filter_part(right.trim())
		filter_part.operator = get_operator('-')
		return filter_part
	}

	if (!arithmetic_operators.some((operator) => expression.includes(operator))) {
		// no arithmetic operator
		// parse as column if it's a column else parse as value
		return is_column(expression)
			? get_column(expression)
			: {
					label: expression.trim(),
					value: expression.trim(),
			  }
	}
}
function is_column(string) {
	return string.includes('[') && string.includes(']')
}
function get_column(string) {
	const start_index = string.lastIndexOf('[')
	const end_index = string.indexOf(']')
	const column_label = string.slice(start_index + 1, end_index)
	const column = selectedColumns.value[column_label]
	return column
}
function get_compare_operator() {
	const regex = new RegExp(compare_operators.join('|'), 'g')
	const compare_operator = input.value.match(regex)

	if (!compare_operator) {
		$notify({
			title: 'Please enter a valid compare operator',
			message: 'Make sure operator has a space before and after it',
			appearance: 'warning',
		})
		return
	}

	if (compare_operator.length > 1) {
		$notify({
			title: 'Only one compare operator is allowed',
			message: `You have entered ${compare_operator.length} operators: ${compare_operator.join(',')}`,
			appearance: 'warning',
		})
		return
	}

	return get_operator(compare_operator[0])
}
function get_operator(operator_value) {
	const operator_label_map = {
		' = ': 'equals',
		' != ': 'not equals',
		' > ': 'greater than',
		' < ': 'less than',
		' >= ': 'greater than equal to',
		' <= ': 'less than equal to',
	}
	const operator_label = operator_label_map[operator_value] || operator_value.trim()
	return {
		label: operator_label,
		value: operator_value.trim(),
	}
}

function auto_add_close_square_brackets(e) {
	// check if any modifiers are pressed
	const modifiers = [e.ctrlKey, e.altKey, e.shiftKey, e.metaKey]
	if (modifiers.some(Boolean)) {
		return
	}

	if (e.keyCode === 219) {
		// if open square bracket button is clicked,
		// append close square bracket after caret position
		input.value = input.value.slice(0, caretPosition.value) + '] ' + input.value.slice(caretPosition.value)
		nextTick(() => {
			// set caret position before close square bracket
			e.target.setSelectionRange(caretPosition.value, caretPosition.value)
		})
	}
}
function auto_remove_close_square_bracket(e) {
	// check if any modifiers are pressed
	const modifiers = [e.ctrlKey, e.altKey, e.shiftKey, e.metaKey]
	if (modifiers.some(Boolean)) {
		return
	}

	// if backspace is pressed,
	if (e.keyCode === 8) {
		// if backspace is pressed,
		// check if deleted character is an open square bracket
		// if yes, remove close square bracket after caret position
		const deleted_character = input.value.slice(caretPosition.value - 1, caretPosition.value)
		if (deleted_character === '[' && input.value.charAt(caretPosition.value) === ']') {
			nextTick(() => {
				input.value = input.value.slice(0, caretPosition.value - 1) + input.value.slice(caretPosition.value + 1)
			})
		}
	}
}
function auto_add_quotes(e) {
	// check if any modifiers are pressed except shift
	const modifiers = [e.ctrlKey, e.altKey, e.metaKey]
	if (modifiers.some(Boolean)) {
		return
	}

	if (e.keyCode === 222 && e.shiftKey) {
		// if open quote button is clicked,
		// append close quote after caret position
		input.value = input.value.slice(0, caretPosition.value) + '"' + input.value.slice(caretPosition.value)
		nextTick(() => {
			// set caret position before close quote
			e.target.setSelectionRange(caretPosition.value, caretPosition.value)
		})
	}
}
function auto_remove_quotes(e) {
	// check if any modifiers are pressed except shift
	const modifiers = [e.ctrlKey, e.altKey, e.metaKey]
	if (modifiers.some(Boolean)) {
		return
	}

	// if backspace is pressed,
	if (e.keyCode === 8) {
		// if backspace is pressed,
		// check if deleted character is an open square bracket
		// if yes, remove close square bracket after caret position
		const deleted_character = input.value.slice(caretPosition.value - 1, caretPosition.value)
		if (deleted_character === '"' && input.value.charAt(caretPosition.value) === '"') {
			nextTick(() => {
				input.value = input.value.slice(0, caretPosition.value - 1) + input.value.slice(caretPosition.value + 1)
			})
		}
	}
}
</script>
