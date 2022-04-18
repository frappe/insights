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
					v-if="suggestions?.length"
					:suggestions="suggestions"
					@select="(suggestion) => on_suggestion_select(suggestion)"
				/>
			</template>
		</Popover>
	</div>
</template>

<script>
import { ref } from 'vue'
import SuggestionBox from './SuggestionBox.vue'

export default {
	name: 'FilterSearch',
	props: ['tables', 'query', 'filter'],
	components: {
		SuggestionBox,
	},
	setup(props) {
		const { filter } = props
		let [_filter, input_value, input_focused, now_selecting] = [null, null, null, null]

		if (filter && filter.left.label && filter.operator.label && filter.right.label) {
			input_value = ref(`${filter.left.label};${filter.operator.label};${filter.right.label};`)
			input_focused = ref(false)
			now_selecting = ref('right')
			_filter = ref(filter)
		} else {
			input_value = ref('')
			input_focused = ref(false)
			now_selecting = ref('left')
			_filter = ref({
				left: {},
				operator: {},
				right_type: '',
				right: {},
			})
		}
		return { input_value, input_focused, now_selecting, filter: _filter }
	},
	mounted() {
		this.$refs.filter_picker?.focus()
		this.query.get_selectable_columns.fetch({ tables: this.tables })
		if (this.filter?.left?.type) {
			this.$resources.operator_list.submit({ fieldtype: this.filter.left.type })
		}

		// // detect click outside of input
		// document.addEventListener('click', (e) => {
		// 	if (e.target.closest('.filter-picker') || e.target.classList.contains('filter-picker-suggestion')) {
		// 		return this.$refs.filter_picker?.focus()
		// 	}
		// 	this.input_focused = false
		// })
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

				if (this.filter.right_type != 'Column') {
					let _suggestion = [{ label: 'Type a value...', is_header: true }]
					const right_input = this.input_value.split(';')[2]
					if (right_input?.length > 0) {
						_suggestion = [
							{ label: 'Press enter to confirm', is_header: true },
							{ label: right_input, value: right_input },
						]
					}
					return _suggestion
				}
			}
		},
	},
	watch: {
		// now_selecting(value) {
		// 	if (value === 'left') {
		// 		.then(() => {
		// 			const filter_picker = this.$refs.filter_picker
		// 			const scrollable_parent = filter_picker.closest('.overflow-scroll')
		// 			nextTick(() => {
		// 				scrollable_parent.scrollTo({ behaviour: 'smooth', top: scrollable_parent.offsetHeight })
		// 			})
		// 		})
		// 	}
		// },
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
				return
			}

			const right_input = this.input_value.split(';')[2]
			if (delimiter_count === 2 && !right_input) {
				this.filter.right_type = ''
				this.filter.right = {}
				this.now_selecting = 'right_type'
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
				this.$resources.operator_list.submit({ fieldtype: suggestion.type })
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
	},
}
</script>
