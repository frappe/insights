<template>
	<div class="flex flex-col">
		<div class="text-sm font-light text-gray-600">Expression</div>
		<div id="expression_filter_picker" class="relative z-10 mt-1 w-full rounded-md shadow-sm">
			<Popover :show="show">
				<template #target>
					<div class="relative">
						<input
							type="text"
							autocomplete="off"
							spellcheck="false"
							v-model="input"
							ref="filter_input"
							@focus="show = true"
							@keydown.esc.exact="show = false"
							class="form-input block h-8 w-full select-none rounded-md p-0 pl-5 tracking-widest placeholder-gray-500 caret-black"
							:class="{
								'focus:rounded-b-none focus:bg-white focus:shadow': show && options?.length && filtered_options?.length,
							}"
						/>
						<div class="absolute top-0 left-0 flex h-8 items-center pl-2 text-gray-700">=</div>
					</div>
				</template>
				<template #content>
					<SuggestionBox
						v-if="show && options?.length && filtered_options?.length"
						:header_and_suggestions="filtered_options"
						@option-select="on_option_select"
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

<script>
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

import SuggestionBox from '@/components/SuggestionBox.vue'
import { nextTick } from '@vue/runtime-core'
import { debounce } from 'frappe-ui'

export default {
	name: 'ExpressionFilterPicker',
	props: ['query', 'filter'],
	components: {
		SuggestionBox,
	},
	data() {
		const input = this.filter?.expression || ''
		const selected_columns = this.filter ? get_columns_from_filter(this.filter) : {}

		return {
			input,
			selected_columns,
			show: false,
			caret_position: null,
			string_around_caret: '',
			show_columns: false,
		}
	},
	mounted() {
		this.query.get_selectable_columns.fetch()
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest(`#expression_filter_picker`)) {
				return this.$refs.filter_input?.focus()
			}
			this.show = false
		}
		document.addEventListener('click', this.outside_click_listener)

		// detect caret position
		this.input_keyup_listener = (e) => {
			this.caret_position = e.target.selectionStart

			this.auto_add_close_square_brackets(e)
			this.auto_add_quotes(e)
		}
		this.input_keydown_listener = (e) => {
			this.caret_position = e.target.selectionStart

			this.auto_remove_close_square_bracket(e)
			this.auto_remove_quotes(e)
		}
		this.$refs.filter_input?.addEventListener('keydown', this.input_keydown_listener)
		this.$refs.filter_input?.addEventListener('keyup', this.input_keyup_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
		this.$refs.filter_input?.addEventListener('keydown', this.input_keydown_listener)
		this.$refs.filter_input?.removeEventListener('keyup', this.input_keyup_listener)
	},
	watch: {
		show(val) {
			val ? this.$refs.filter_input?.focus() : this.$refs.filter_input?.blur()
		},
		input(new_input) {
			// if new_input doesn't contains selected_columns keys, remove them
			for (let key of Object.keys(this.selected_columns)) {
				if (!new_input.includes(`[${key}]`)) {
					delete this.selected_columns[key]
				}
			}
		},
		caret_position: debounce(function (new_caret_position) {
			// get string around caret between sqaure brackets
			const input = this.input
			const start_index = input.lastIndexOf('[', new_caret_position)
			const end_index = input.indexOf(']', new_caret_position)
			const string_around_caret = input.slice(start_index + 1, end_index > 0 ? end_index : input.length)

			if (string_around_caret.length && (!string_around_caret.includes('[') || !string_around_caret.includes(']'))) {
				this.show_columns = true
				this.string_around_caret = string_around_caret
			} else {
				this.show_columns = false
				this.string_around_caret = ''
			}
		}, 200),
	},
	computed: {
		column_list() {
			return this.query.get_selectable_columns?.data?.message || []
		},
		column_options() {
			return this.column_list.map((c) => ({ ...c, secondary_label: c.table_label }))
		},
		options() {
			return this.show_columns ? this.column_options : []
		},
		filtered_options() {
			return this.string_around_caret
				? this.options.filter((o) => o.label.toLowerCase().includes(this.string_around_caret.toLowerCase()))
				: this.options
		},
	},
	methods: {
		on_option_select(suggestion) {
			let start_index = this.input.lastIndexOf('[', this.caret_position)
			let end_index = this.input.indexOf(']', this.caret_position)
			end_index = end_index > 0 ? end_index : this.input.length

			const left_part = this.input.slice(0, start_index + 1)
			const right_part = this.input.slice(end_index)
			const new_input = left_part + `[${suggestion.label}]` + right_part
			this.input = new_input.replaceAll('[[', '[').replaceAll(']]', ']')

			this.selected_columns[suggestion.label] = suggestion

			this.show_columns = false
			this.string_around_caret = ''

			this.$refs.filter_input?.focus()
		},
		apply() {
			const filter = this.build_filter()
			if (filter) {
				this.$emit('filter-select', { filter })
				this.show = false
			}
		},
		build_filter() {
			const filter = { is_expression: true, expression: this.input }
			filter.operator = this.get_compare_operator()

			if (!filter.operator) {
				return
			}

			const [left, right] = this.input.split(filter.operator.value)
			filter.left = this.build_filter_part(left)
			filter.right = this.build_filter_part(right)

			return filter
		},
		build_filter_part(expression) {
			let filter_part = {}

			if (expression.includes('/')) {
				const [left, right] = expression.split('/')
				filter_part.left = this.build_filter_part(left.trim())
				filter_part.right = this.build_filter_part(right.trim())
				filter_part.operator = this.get_operator('/')
				return filter_part
			}
			if (expression.includes('*')) {
				const [left, right] = expression.split('*')
				filter_part.left = this.build_filter_part(left.trim())
				filter_part.right = this.build_filter_part(right.trim())
				filter_part.operator = this.get_operator('*')
				return filter_part
			}
			if (expression.includes('+')) {
				const [left, right] = expression.split('+')
				filter_part.left = this.build_filter_part(left.trim())
				filter_part.right = this.build_filter_part(right.trim())
				filter_part.operator = this.get_operator('+')
				return filter_part
			}
			if (expression.includes('-')) {
				const [left, right] = expression.split('-')
				filter_part.left = this.build_filter_part(left.trim())
				filter_part.right = this.build_filter_part(right.trim())
				filter_part.operator = this.get_operator('-')
				return filter_part
			}

			if (!arithmetic_operators.some((operator) => expression.includes(operator))) {
				// no arithmetic operator
				// parse as column if it's a column else parse as value
				return this.is_column(expression)
					? this.get_column(expression)
					: {
							label: expression.trim(),
							value: expression.trim(),
					  }
			}
		},
		is_column(string) {
			return string.includes('[') && string.includes(']')
		},
		get_column(string) {
			const start_index = string.lastIndexOf('[')
			const end_index = string.indexOf(']')
			const column_label = string.slice(start_index + 1, end_index)
			const column = this.selected_columns[column_label]
			return column
		},
		get_compare_operator() {
			const regex = new RegExp(compare_operators.join('|'), 'g')
			const compare_operator = this.input.match(regex)

			if (!compare_operator) {
				this.$notify({
					title: 'Please enter a valid compare operator',
					message: 'Make sure operator has a space before and after it',
					appearance: 'warning',
				})
				return
			}

			if (compare_operator.length > 1) {
				this.$notify({
					title: 'Only one compare operator is allowed',
					message: `You have entered ${compare_operator.length} operators: ${compare_operator.join(',')}`,
					appearance: 'warning',
				})
				return
			}

			return this.get_operator(compare_operator[0])
		},
		get_operator(operator_value) {
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
		},

		// key events on input
		auto_add_close_square_brackets(e) {
			// check if any modifiers are pressed
			const modifiers = [e.ctrlKey, e.altKey, e.shiftKey, e.metaKey]
			if (modifiers.some(Boolean)) {
				return
			}

			if (e.keyCode === 219) {
				// if open square bracket button is clicked,
				// append close square bracket after caret position
				this.input = this.input.slice(0, this.caret_position) + '] ' + this.input.slice(this.caret_position)
				nextTick(() => {
					// set caret position before close square bracket
					e.target.setSelectionRange(this.caret_position, this.caret_position)
				})
			}
		},
		auto_remove_close_square_bracket(e) {
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
				const deleted_character = this.input.slice(this.caret_position - 1, this.caret_position)
				if (deleted_character === '[' && this.input.charAt(this.caret_position) === ']') {
					nextTick(() => {
						this.input = this.input.slice(0, this.caret_position - 1) + this.input.slice(this.caret_position + 1)
					})
				}
			}
		},
		auto_add_quotes(e) {
			// check if any modifiers are pressed except shift
			const modifiers = [e.ctrlKey, e.altKey, e.metaKey]
			if (modifiers.some(Boolean)) {
				return
			}

			if (e.keyCode === 222 && e.shiftKey) {
				// if open quote button is clicked,
				// append close quote after caret position
				this.input = this.input.slice(0, this.caret_position) + '"' + this.input.slice(this.caret_position)
				nextTick(() => {
					// set caret position before close quote
					e.target.setSelectionRange(this.caret_position, this.caret_position)
				})
			}
		},
		auto_remove_quotes(e) {
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
				const deleted_character = this.input.slice(this.caret_position - 1, this.caret_position)
				if (deleted_character === '"' && this.input.charAt(this.caret_position) === '"') {
					nextTick(() => {
						this.input = this.input.slice(0, this.caret_position - 1) + this.input.slice(this.caret_position + 1)
					})
				}
			}
		},
	},
}

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
</script>
