<template>
	<div class="flex flex-col">
		<div class="text-sm font-light text-gray-600">Expression</div>
		<div id="expression_filter_picker" class="relative z-10 mt-1 w-full rounded-md shadow-sm">
			<Popover :show="input_focused">
				<template #target>
					<div class="relative">
						<input
							type="text"
							autocomplete="off"
							spellcheck="false"
							v-model="input"
							ref="filter_input"
							@focus="input_focused = true"
							@blur="input_focused = false"
							@keydown.esc.exact="$refs.filter_input.blur()"
							class="form-input block h-8 w-full select-none rounded-md pl-5 text-sm tracking-widest placeholder-gray-500"
							:class="{
								'focus:rounded-b-none focus:bg-white focus:shadow':
									input_focused && options?.length && filtered_options?.length,
							}"
						/>
						<div class="absolute top-0 left-0 flex h-8 items-center pl-2 text-lg text-gray-700">=</div>
					</div>
				</template>
				<template #content>
					<SuggestionBox
						v-if="input_focused && options?.length && filtered_options?.length"
						:header_and_suggestions="filtered_options"
						@select="on_option_select"
					/>
				</template>
			</Popover>
		</div>
		<div class="mt-2 rounded-md border border-orange-50 bg-orange-50/80 p-2 text-sm font-light text-gray-500">
			You can use following operators:
			<span class="font-medium tracking-widest"> +, -, *, /, =, !=, &lt;, &gt;, &lt;=, &gt;= </span> <br />
			You can select a column by typing <span class="font-medium tracking-widest"> [column_name] </span>
		</div>
		<div class="mt-3 flex justify-end">
			<Button appearance="primary" @click="apply"> Apply </Button>
		</div>
	</div>
</template>

<script>
import SuggestionBox from '@/components/SuggestionBox.vue'
import { nextTick } from '@vue/runtime-core'

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
			input_focused: false,
			caret_position: null,
			string_around_caret: '',
			show_column_list: false,
		}
	},
	mounted() {
		this.query.get_selectable_columns.fetch()
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest(`#expression_filter_picker`)) {
				return this.$refs.filter_input?.focus()
			}
			this.input_focused = false
		}
		document.addEventListener('click', this.outside_click_listener)

		// detect caret position
		this.input_keyup_listener = (e) => {
			this.caret_position = e.target.selectionStart

			if (e.keyCode === 219) {
				// check if any modifiers are pressed
				const modifiers = [e.ctrlKey, e.altKey, e.shiftKey, e.metaKey]
				if (modifiers.some(Boolean)) {
					return
				}
				// if open square bracket button is clicked,
				// append close square bracket after caret position
				this.input = this.input.slice(0, this.caret_position) + '] ' + this.input.slice(this.caret_position)
				nextTick(() => {
					// set caret position before close square bracket
					e.target.setSelectionRange(this.caret_position, this.caret_position)
				})
			}
		}
		this.$refs.filter_input?.addEventListener('keyup', this.input_keyup_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
		this.$refs.filter_input?.removeEventListener('keyup', this.input_keyup_listener)
	},
	watch: {
		input(new_input) {
			// if new_input doesn't contains selected_columns keys, remove them
			for (let key of Object.keys(this.selected_columns)) {
				if (!new_input.includes(`[${key}]`)) {
					delete this.selected_columns[key]
				}
			}
		},
		caret_position(new_caret_position) {
			// get string around caret between sqaure brackets
			const input = this.input
			const start_index = input.lastIndexOf('[', new_caret_position)
			const end_index = input.indexOf(']', new_caret_position)
			const string_around_caret = input.slice(start_index + 1, end_index > 0 ? end_index : input.length)

			if (string_around_caret.length && (!string_around_caret.includes('[') || !string_around_caret.includes(']'))) {
				this.show_column_list = true
				this.string_around_caret = string_around_caret
			} else {
				this.show_column_list = false
				this.string_around_caret = ''
			}
		},
	},
	computed: {
		column_list() {
			// Column: { label, table, table_label, column, type }
			return this.query.get_selectable_columns?.data?.message || []
		},
		options() {
			return this.show_column_list ? this.column_list : []
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
		},
		reset() {
			this.$refs.filter_input?.blur()
			this.input_focused = false
		},
		apply() {
			const filter = this.build_filter()
			if (filter) {
				this.$emit('filter-select', { filter })
				this.reset()
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
			const arithmetic_operators = ['+', '-', '*', '/']

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
			const compare_operator = this.input.match(/(=|!=|>|<|>=|<=)/g)

			if (!compare_operator) {
				this.$notify({
					title: 'Please enter a valid compare operator',
					icon: 'alert-circle',
					color: 'red',
				})
				return
			}

			if (compare_operator.length > 1) {
				this.$notify({
					title: 'Only one compare operator is allowed',
					icon: 'alert-circle',
					color: 'red',
				})
				return
			}

			return this.get_operator(compare_operator[0])
		},
		get_operator(operator_value) {
			switch (operator_value) {
				case '=':
					return {
						value: '=',
						label: 'equals',
					}
				case '!=':
					return {
						value: '!=',
						label: 'not equals',
					}
				case '>':
					return {
						value: '>',
						label: 'greater than',
					}
				case '<':
					return {
						value: '<',
						label: 'less than',
					}
				case '>=':
					return {
						value: '>=',
						label: 'greater than equal to',
					}
				case '<=':
					return {
						value: '<=',
						label: 'less than equal to',
					}
				default:
					return {
						value: operator_value,
						label: operator_value,
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
