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
					class="form-input block h-8 flex-1 select-none whitespace-nowrap rounded-md border-gray-300 text-sm text-transparent placeholder-gray-500 caret-black focus:bg-gray-100"
					placeholder="Select a column..."
					@focus="input_focused = true"
					@keydown.tab="input_focused = false"
				/>
				<div
					v-if="input_value"
					class="absolute top-0 flex h-9 w-full cursor-text items-center whitespace-nowrap border border-transparent px-3 text-sm leading-6"
					@click="$refs.filter_picker.focus()"
				>
					{{ input_value.replace(/;/g, ' ') }}
				</div>
			</template>
			<template #content>
				<SuggestionBox
					v-if="input_focused && suggestions?.length"
					:suggestions="suggestions"
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

		if (props.filter && props.filter.left.label && props.filter.operator.label && props.filter.right.label) {
			data.filter = ref(props.filter)
			data.now_selecting = ref('right')
			data.input_value = ref(`${props.filter.left.label};${props.filter.operator.label};;${props.filter.right.label}`)
		}

		return data
	},
	mounted() {
		this.$refs.filter_picker?.focus()
		this.query.get_selectable_columns.fetch({ tables: this.tables })
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

			if (this.now_selecting === 'right_type') {
				const static_value_type = this.get_static_value_type(this.filter.left.type)
				return [{ label: 'Select value type...', is_header: true }, { label: static_value_type }, { label: 'Column' }]
			}

			if (this.now_selecting === 'right') {
				if (this.filter.right_type == 'Column') {
					_suggestions = [{ label: 'Select a column...', is_header: true }]
					_suggestions = _suggestions.concat(this.get_column_suggestions(right))
					return _suggestions
				}

				if (this.filter.right_type !== 'Column') {
					return this.get_value_suggestions()
				}
			}
		},
	},
	watch: {
		input_value(new_value) {
			const delimiter_count = (new_value.match(/;/g) || []).length
			if (delimiter_count === 0) {
				this.filter.left = {}
				this.filter.operator = {}
				this.filter.right_type = ''
				this.filter.right = {}
				this.now_selecting = 'left'
				return
			}

			if (delimiter_count === 1) {
				this.filter.operator = {}
				this.filter.right_type = ''
				this.filter.right = {}
				this.now_selecting = 'operator'
				this.$resources.operator_list.submit({
					fieldtype: this.filter.left.type,
				})
				return
			}

			if (delimiter_count === 2) {
				this.filter.right_type = ''
				this.filter.right = {}
				this.now_selecting = 'right_type'
				return
			}

			const right_input = this.input_value.split(';').at(-1)
			if (delimiter_count === 3 && right_input) {
				this.check_and_fetch_column_values(right_input)
				return
			}
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			if (this.now_selecting === 'left') {
				this.filter.left = suggestion
				this.input_value = `${suggestion.label};`
				this.$refs.filter_picker?.focus()
				this.now_selecting = 'operator'
				return
			}

			if (this.now_selecting === 'operator') {
				this.filter.operator = suggestion
				this.input_value = `${this.filter.left.label};${suggestion.label};`
				this.$refs.filter_picker?.focus()
				this.now_selecting = 'right_type'
				return
			}

			if (this.now_selecting === 'right_type') {
				this.filter.right_type = suggestion.label
				this.input_value = `${this.filter.left.label};${this.filter.operator.label};;`
				this.$refs.filter_picker?.focus()
				this.now_selecting = 'right'
				return
			}

			if (this.now_selecting === 'right') {
				this.filter.right = suggestion
				this.$emit('filter_selected', this.filter)
				this.reset()
				return
			}
		},
		reset() {
			this.filter = {
				left: {},
				operator: {},
				right_type: '',
				right: {},
			}
			this.input_value = ''
			this.input_focused = false
			this.now_selecting = null
			this.$refs.column_search?.blur()
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

			if (this.filter.right_type === 'Text' && this.column_value_list.length) {
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
				this.filter.right_type === 'Text' &&
				valid_operators.includes(this.filter.operator.label)
			) {
				this.query.get_column_values.submit({
					column: this.filter.left,
					search_text: right_input,
				})
			}
		}, 200),
	},
}
</script>
