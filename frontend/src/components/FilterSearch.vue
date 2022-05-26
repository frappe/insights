<template>
	<div class="filter-picker relative z-10 flex w-fit flex-1">
		<Popover :show="input_focused">
			<template #target>
				<input
					type="text"
					ref="filter_picker"
					v-model="input_value"
					spellcheck="false"
					autocomplete="off"
					:size="Math.max(input_value.length, 20) || 20"
					class="form-input block h-8 max-w-sm flex-1 select-none whitespace-nowrap rounded-md text-sm text-transparent placeholder-gray-500 caret-black focus:bg-gray-100"
					placeholder="Select a column..."
					@focus="input_focused = true"
					@keydown.tab="input_focused = false"
				/>
				<div
					v-if="input_value"
					class="absolute top-0 flex h-8 w-full max-w-sm origin-right cursor-text items-center whitespace-nowrap px-3 text-sm"
					@click="$refs.filter_picker.focus()"
				>
					{{ input_value.replace(/;/g, ' ') }}
				</div>
			</template>
			<template #content>
				<SuggestionBox
					v-if="input_focused && suggestions?.length"
					:header_and_suggestions="suggestions"
					@select="(suggestion) => on_suggestion_select(suggestion)"
				/>
			</template>
		</Popover>
	</div>
</template>

<script>
import { ref } from 'vue'
import { debounce } from 'frappe-ui'
import SuggestionBox from './SuggestionBox.vue'

export default {
	name: 'FilterSearch',
	props: ['tables', 'query', 'filter'],
	components: {
		SuggestionBox,
	},
	setup(props) {
		const data = {
			input_value: ref(''),
			input_focused: ref(false),
			now_selecting: ref('left'),
			filter: ref({
				left: {},
				operator: {},
				right_type: '',
				right: {},
			}),
		}

		if (props.filter && props.filter.left.label && props.filter.operator.label) {
			data.filter = ref(props.filter)

			const filter = props.filter
			if (filter.operator.value.includes('set')) {
				data.now_selecting = ref('operator')
				data.input_value = ref(`${filter.left.label};${filter.operator.label}`)
			} else if (filter.right_type == 'Column') {
				data.now_selecting = ref('right')
				data.input_value = ref(`${filter.left.label};${filter.operator.label};[${filter.right.label}]`)
			} else {
				data.now_selecting = ref('right')
				data.input_value = ref(`${filter.left.label};${filter.operator.label};${filter.right.label}`)
			}
		}

		return data
	},
	mounted() {
		this.$refs.filter_picker?.focus()
		this.query.get_selectable_columns.submit()
		this.fetch_operators()
		if (this.filter.right_type == 'Column') {
			this.$refs.filter_picker?.setSelectionRange(this.input_value.length - 1, this.input_value.length - 1)
		}
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest('.filter-picker')) {
				return this.$refs.filter_picker?.focus()
			}
			this.input_focused = false
		}
		document.addEventListener('click', this.outside_click_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
	resources: {
		operator_list() {
			return {
				method: 'analytics.api.get_operator_list',
			}
		},
	},
	computed: {
		column_list() {
			// Column: { label, table, table_label, column, type }
			return this.query.get_selectable_columns?.data?.message || []
		},
		operator_list() {
			// Operator: { label, value }
			return this.$resources.operator_list.data || []
		},
		column_value_list() {
			return this.query.get_column_values?.data?.message || []
		},
		suggestions() {
			let _suggestions = []
			const [left, operator, right] = this.input_value.split(';')

			if (this.now_selecting === 'left') {
				return this.get_column_suggestions(left)
			}

			if (this.now_selecting === 'operator') {
				return this.get_operator_suggestions(operator)
			}

			if (this.now_selecting === 'right') {
				if (this.filter.right_type === 'Column') {
					_suggestions = [{ label: 'Select a column...', is_header: true }]
					_suggestions = _suggestions.concat(this.get_column_suggestions(right.slice(1, -1)))
					return _suggestions
				}

				return this.get_value_suggestions()
			}
		},
	},
	watch: {
		input_value(new_value) {
			const delimiter_count = (new_value.match(/;/g) || []).length
			if (delimiter_count === 0) {
				this.reset_left()
				return
			}

			if (delimiter_count === 1) {
				this.reset_operator()
				this.fetch_operators()
				return
			}

			const right_input = this.input_value.split(';').at(-1)
			const allow_compare_with_column = ['=', '>', '<', '>=', '<='].includes(this.filter.operator.value)

			if (delimiter_count === 2 && right_input && allow_compare_with_column) {
				if (right_input.endsWith('[')) {
					this.input_value += ']'
					this.$nextTick(() => {
						// set caret postion before closing bracket
						this.$refs.filter_picker?.setSelectionRange(this.input_value.length - 1, this.input_value.length - 1)
					})
					return
				}

				if (right_input == ']') {
					// remove last character
					this.input_value = this.input_value.slice(0, -1)
					this.filter.right_type = null
					this.$nextTick(() => {
						this.$refs.filter_picker?.setSelectionRange(this.input_value.length, this.input_value.length)
					})
					return
				}

				if (right_input.startsWith('[') && right_input.endsWith(']')) {
					this.filter.right_type = 'Column'
				} else {
					this.filter.right_type = null
				}
			}

			const operator_is_equal = this.filter.operator.value === '='
			if (delimiter_count === 2 && right_input && operator_is_equal) {
				this.check_and_fetch_column_values(right_input)
				return
			}
		},
		now_selecting(newVal) {
			if (newVal) {
				!this.input_focused && this.$refs.filter_picker?.focus()
			} else {
				this.input_focused && this.$refs.filter_picker?.blur()
			}
		},
		'filter.operator.value': function (operator) {
			if (!operator) return

			if (operator.includes('set')) {
				this.filter.right = {}
				this.trigger_filter_select()
				return
			}
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			if (this.now_selecting === 'left') {
				this.filter.left = suggestion
				this.input_value = `${suggestion.label};`
				this.now_selecting = 'operator'
				return
			}

			if (this.now_selecting === 'operator') {
				this.filter.operator = suggestion
				this.input_value = `${this.filter.left.label};${suggestion.label};`
				this.now_selecting = 'right'
				return
			}

			if (this.now_selecting === 'right') {
				this.filter.right = suggestion
				this.trigger_filter_select()
				return
			}
		},
		trigger_filter_select() {
			this.$emit('filter_selected', this.filter)
			this.reset()
		},
		reset() {
			this.filter = {
				left: {},
				operator: {},
				right_type: null,
				right: {},
			}
			this.input_value = ''
			this.input_focused = false
			this.now_selecting = null
		},
		get_icon_for(column_type) {
			if (['varchar', 'char', 'enum', 'text', 'longtext'].includes(column_type.toLowerCase())) {
				return 'type'
			}
			if (['int', 'decimal', 'bigint', 'float', 'double'].includes(column_type.toLowerCase())) {
				return 'hash'
			}
			if (['date', 'datetime', 'time', 'timestamp'].includes(column_type.toLowerCase())) {
				return 'clock'
			}
		},
		get_static_value_type(column_type) {
			if (['varchar', 'char', 'enum', 'text', 'longtext'].includes(column_type.toLowerCase())) {
				return 'Text'
			}
			if (['int', 'decimal', 'bigint', 'float', 'double'].includes(column_type.toLowerCase())) {
				return 'Number'
			}
			if (['date', 'datetime', 'time', 'timestamp'].includes(column_type.toLowerCase())) {
				return column_type
			}
		},
		get_column_suggestions(input) {
			let _suggestions = []
			if (input) {
				_suggestions = this.column_list.filter((c) => c.label.toLowerCase().includes(input.toLowerCase()))
			} else {
				_suggestions = this.column_list
			}
			_suggestions.forEach((c) => {
				c.icon = this.get_icon_for(c.type)
				c.secondary_label = c.table_label
			})
			return _suggestions
		},
		get_operator_suggestions(input) {
			let _suggestions = [{ label: 'Select an operator...', is_header: true }]
			if (input) {
				_suggestions = _suggestions.concat(
					this.operator_list.filter((o) => o.label.toLowerCase().includes(input.toLowerCase()))
				)
			} else {
				_suggestions = _suggestions.concat(this.operator_list)
			}
			return _suggestions
		},
		get_value_suggestions() {
			const right_input = this.input_value.split(';').at(-1)

			if (!right_input) {
				return [{ label: 'Type a value...', is_header: true }]
			}

			const right_is_a_list = this.filter.operator.value.includes('in')
			if (right_is_a_list) {
				return [
					{ label: 'Enter comma separated values...', is_header: true },
					{ label: right_input, value: right_input },
				]
			}

			if (this.column_value_list.length) {
				return [{ label: 'Press enter to confirm', is_header: true }, ...this.column_value_list]
			}

			if (right_input.length > 0) {
				return [
					{ label: 'Press enter to confirm', is_header: true },
					{ label: right_input, value: right_input },
				]
			}
		},
		check_and_fetch_column_values: debounce(function (right_input) {
			// do not show column values for long text columns
			const left_is_smalltext = ['varchar', 'char', 'enum'].includes(this.filter.left.type.toLowerCase())
			// do not show column values for 'like', 'starts with', 'ends with' etc. operators
			const valid_operators = ['equals', 'not equals', 'in', 'not in']

			if (
				left_is_smalltext &&
				this.filter.right_type !== 'Column' &&
				valid_operators.includes(this.filter.operator.label)
			) {
				this.query.get_column_values.submit({
					column: this.filter.left,
					search_text: right_input,
				})
			}
		}, 200),
		fetch_operators: debounce(function () {
			if (this.filter.left.type) {
				this.$resources.operator_list.submit({
					fieldtype: this.filter.left.type,
				})
			}
		}, 200),
		reset_left() {
			this.filter.left = {}
			this.filter.operator = {}
			this.filter.right_type = null
			this.filter.right = {}
			this.now_selecting = 'left'
		},
		reset_operator() {
			this.filter.operator = {}
			this.filter.right_type = null
			this.filter.right = {}
			this.now_selecting = 'operator'
		},
		reset_right() {
			this.filter.right_type = null
			this.filter.right = {}
			this.now_selecting = 'right'
		},
	},
}
</script>
