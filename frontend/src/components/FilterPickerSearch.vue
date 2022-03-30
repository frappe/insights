<!-- This example requires Tailwind CSS v2.0+ -->
<template>
	<div class="filter-search relative z-10 w-full rounded-md shadow-sm">
		<input
			type="text"
			ref="filter_search"
			spellcheck="false"
			class="form-input block h-9 w-full select-none rounded-md border-gray-300 text-sm text-transparent placeholder-gray-500 caret-black focus:bg-white focus:shadow"
			:class="{
				'font-semibold': right_input,
				'placeholder:italic placeholder:text-gray-500': focused,
			}"
			:placeholder="focused ? placeholder : 'Add a filter...'"
			v-model="input_value"
			@focus="focused = true"
			@keydown.backspace="on_backspace"
			@keydown.meta.enter="on_enter"
			@keydown.ctrl.enter="on_enter"
		/>
		<div
			v-if="input_value"
			class="absolute top-0 flex h-9 w-full cursor-text items-center border border-transparent px-3 text-sm leading-6"
		>
			<span class="mr-1 font-medium">
				{{ left_input }}
			</span>

			<span
				v-if="is_left_selected && !operator_input"
				class="mr-1 font-light italic text-gray-500"
			>
				{{ placeholder }}
			</span>
			<span v-else class="mr-1 font-light">
				{{ operator_input }}
			</span>

			<span
				v-if="is_left_selected && is_operator_selected && !right_input"
				class="mr-1 font-light italic text-gray-500"
			>
				{{ placeholder }}
			</span>
			<span v-else class="font-semibold">
				{{ right_input }}
			</span>
		</div>
		<div
			class="absolute inset-y-0 right-0 flex items-center pr-3 transition-all hover:scale-110"
		>
			<FeatherIcon
				v-if="focused && input_value"
				name="check-circle"
				class="h-4 w-4 cursor-pointer text-gray-400"
				:class="{
					'text-green-500': left_input && operator_input && right_input,
				}"
				aria-hidden="true"
			/>
		</div>

		<transition
			enter-active-class="transition ease-out duration-100"
			enter-from-class="transform opacity-0 scale-95"
			enter-to-class="transform opacity-100 scale-100"
			leave-active-class="transition ease-in duration-75"
			leave-from-class="transform opacity-100 scale-100"
			leave-to-class="transform opacity-0 scale-95"
		>
			<div
				v-if="focused && suggestions.length != 0"
				class="absolute top-8 mt-2 max-h-52 w-full origin-top overflow-scroll overflow-x-hidden rounded-md bg-white shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none"
			>
				<div
					v-for="item in suggestions"
					:key="item.label"
					class="suggestion flex cursor-default items-center justify-between rounded-md px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
					@click.prevent="on_suggestion_select(item)"
				>
					<div class="flex items-center">
						<div class="font-semibold">{{ item.label }}</div>
					</div>
					<div v-if="item.table_label" class="flex font-light text-gray-500">
						{{ item.table_label }}&nbsp;&#8226;&nbsp;{{ item.type }}
					</div>
				</div>
			</div>
		</transition>
	</div>
</template>

<script>
export default {
	props: ['tables', 'should_focus', 'query'],
	data() {
		return {
			focused: false,
			input_value: '',
			delimiter: ';',
			filter: {
				left: {},
				operator: {},
				right: {},
			},
		}
	},
	mounted() {
		// detect click outside of input
		document.addEventListener('click', (e) => {
			if (
				e.target.closest('.filter-search') ||
				e.target.classList.contains('suggestion')
			) {
				return this.$refs.filter_search?.focus()
			}
			this.focused = false
		})
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
		placeholder() {
			const [left, operator, right] = this.input_value.split(this.delimiter)
			if (!this.is_left_selected) {
				return 'Select a column...'
			} else if (this.is_left_selected && !operator) {
				return 'select an operator...'
			} else if (this.is_left_selected && this.is_operator_selected && !right) {
				return !this.filter.right.value_type
					? 'select value type...'
					: this.filter.right.value_type == 'Column'
					? 'select a column...'
					: 'type a value...'
			}
		},
		operator_list() {
			// Operator: { label, value }
			return this.$resources.operator_list.data || []
		},
		is_left_selected() {
			const regex = RegExp(`${this.delimiter}`, 'g')
			return (this.input_value.match(regex) || []).length > 0
		},
		is_operator_selected() {
			const regex = RegExp(`${this.delimiter}`, 'g')
			return (this.input_value.match(regex) || []).length > 1
		},
		is_right_selected() {
			const regex = RegExp(`${this.delimiter}`, 'g')
			return (this.input_value.match(regex) || []).length > 2
		},
		left_input() {
			return this.input_value.split(this.delimiter)[0]
		},
		operator_input() {
			return this.input_value.split(this.delimiter)[1] || ''
		},
		right_input() {
			return this.input_value.split(this.delimiter)[2]
		},
		suggestions() {
			const [left, operator, right] = this.input_value.split(this.delimiter)
			let suggestions = []

			if (!this.is_left_selected) {
				suggestions = left
					? this.column_list.filter((c) =>
							c.label.toLowerCase().includes(left.toLowerCase())
					  )
					: this.column_list
				suggestions = suggestions.map((s) => ({
					...s,
					is_left: true,
				}))
			} else if (!this.is_operator_selected) {
				suggestions = operator
					? this.operator_list.filter((o) => o.label.includes(operator))
					: this.operator_list
				suggestions = suggestions.map((s) => ({
					...s,
					is_operator: true,
				}))
			} else if (!this.is_right_selected) {
				if (this.filter.right.value_type == 'Column') {
					suggestions = right
						? this.column_list.filter((c) =>
								c.label.toLowerCase().includes(right.toLowerCase())
						  )
						: this.column_list
				} else if (this.filter.right.value_type == 'String') {
					suggestions = []
				} else {
					suggestions = [{ label: 'String' }, { label: 'Column' }]
				}
				suggestions = suggestions.map((s) => ({
					...s,
					is_right: true,
				}))
			}

			if (suggestions?.length > 20) {
				suggestions = suggestions.slice(0, 20)
			}

			return suggestions
		},
	},
	watch: {
		focused(is_focused) {
			if (is_focused && !this.is_left_selected) {
				this.query.get_selectable_columns.fetch({ tables: this.tables })
			}
		},
		is_left_selected(newVal, oldVal) {
			if (!newVal && newVal !== oldVal) {
				this.filter.left = {}
				this.filter.operator = {}
				this.filter.right = {}
			}
		},
		is_operator_selected(newVal, oldVal) {
			if (!newVal && newVal !== oldVal) {
				this.filter.operator = {}
				this.filter.right = {}
			}
		},
		is_right_selected(newVal, oldVal) {
			if (!newVal && newVal !== oldVal) {
				this.filter.right = {}
			}
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			if (suggestion.is_left) {
				this.$resources.operator_list.submit({ fieldtype: suggestion.type })
				this.input_value = `${suggestion.label}${this.delimiter}`
				this.filter.left = suggestion
			} else if (suggestion.is_operator) {
				this.input_value = `${this.left_input}${this.delimiter}${suggestion.label}${this.delimiter}`
				this.filter.operator = suggestion
			} else if (suggestion.is_right && !this.filter.right.value_type) {
				this.filter.right.value_type = suggestion.label
				this.input_value = `${this.left_input}${this.delimiter}${this.operator_input}${this.delimiter}`
			} else if (
				suggestion.is_right &&
				this.filter.right.value_type == 'Column'
			) {
				this.input_value = `${this.left_input}${this.delimiter}${this.operator_input}${this.delimiter}${suggestion.label}${this.delimiter}`
				this.filter.right = { ...suggestion, value_type: 'Column' }
			}
		},
		on_backspace(e) {
			// delete the previous selection if a delimiter is deleted
			const last_letter = e.target.value.slice(-1)
			if (last_letter && last_letter == this.delimiter) {
				e.stopPropagation()
				e.preventDefault()
				this.input_value = e.target.value
					.split(this.delimiter) // split by delimiter = [left, operator, '']
					.filter((v) => v) // remove empty values = [left, operator]
					.slice(0, -1) // remove last value = [left]
					.map((v) => `${v}${this.delimiter}`) // add delimiter = ['left;']
					.join('') // join by empty string = left;
			}
		},
		on_enter() {
			if (this.filter.right.value_type == 'String')
				this.filter.right.value = this.right_input

			if (
				this.filter.left.column &&
				this.filter.operator.value &&
				(this.filter.right.column || this.filter.right.value)
			) {
				this.$emit('filter_selected', this.filter)
				this.input_value = ''
				this.focused = false
				this.$refs.filter_search?.blur()
				this.filter = {
					left: {},
					operator: {},
					right: {},
				}
			}
		},
	},
}
</script>
