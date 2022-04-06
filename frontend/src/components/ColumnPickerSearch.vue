<template>
	<div class="column-search relative z-10 w-full rounded-md shadow-sm">
		<input
			type="text"
			ref="column_search"
			autocomplete="off"
			spellcheck="false"
			class="form-input block h-9 w-full select-none rounded-md border-gray-300 text-sm font-medium text-transparent placeholder-gray-500 caret-black focus:bg-white focus:shadow"
			:class="{
				'placeholder:italic placeholder:text-gray-500': focused,
			}"
			:placeholder="focused ? 'Select a table...' : 'Add a column...'"
			v-model="input_value"
			@focus="focused = true"
			@keydown.backspace="on_backspace"
			@keydown.meta.enter="on_enter"
			@keydown.ctrl.enter="on_enter"
		/>
		<div
			v-if="input_value"
			class="absolute top-0 flex h-9 w-full cursor-text items-center border border-transparent px-3 text-sm font-medium leading-6"
		>
			<span class="mr-1">{{ table_input }}</span>

			<span
				v-if="is_left_selected && !column_input"
				class="mr-1 font-light italic text-gray-500"
			>
				Select a column...
			</span>
			<span v-if="column_input" class="mr-1">
				{{ column_input }}
			</span>
		</div>
		<div
			class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
		>
			<FeatherIcon
				v-if="focused && input_value"
				name="check-circle"
				class="h-4 w-4 cursor-pointer text-gray-400"
				:class="{
					'text-green-500': is_table_selected && is_column_selected,
				}"
				aria-hidden="true"
			/>
			<FeatherIcon
				v-else
				name="search"
				class="h-4 w-4 text-gray-400"
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
					v-for="suggestion in suggestions"
					:key="suggestion.label"
					class="column-picker-suggestion flex cursor-default items-center justify-between rounded-md px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
					@click="on_suggestion_select(suggestion)"
				>
					<div class="flex items-center">
						<div class="whitespace-pre font-semibold">
							{{ suggestion.label }}
						</div>
					</div>
					<div
						v-if="suggestion.is_column"
						class="flex font-light text-gray-500"
					>
						{{ suggestion.table_label }}&nbsp;&#8226;&nbsp;{{ suggestion.type }}
					</div>
				</div>
			</div>
		</transition>
	</div>
</template>

<script>
export default {
	props: ['query'],
	data() {
		return {
			table: {},
			column: {},
			focused: false,
			input_value: '',
			delimiter: ';',
		}
	},
	mounted() {
		// detect click outside of input
		document.addEventListener('click', (e) => {
			if (
				e.target.closest('.column-search') ||
				e.target.classList.contains('column-picker-suggestion')
			) {
				return this.$refs.column_search?.focus()
			}
			this.focused = false
		})
	},
	watch: {
		focused(is_focused, old_is_focused) {
			if (is_focused && is_focused != old_is_focused) {
				this.query.get_selectable_tables.fetch()
			}
		},
		is_left_selected(newVal, oldVal) {
			if (!newVal && newVal !== oldVal) {
				this.table = {}
				this.column = {}
			}
		},
		is_operator_selected(newVal, oldVal) {
			if (!newVal && newVal !== oldVal) {
				this.column = {}
			}
		},
	},
	computed: {
		table_list() {
			return this.query.get_selectable_tables?.data?.message || []
		},
		column_list() {
			return this.query.get_selectable_columns?.data?.message || []
		},
		is_table_selected() {
			const regex = RegExp(`${this.delimiter}`, 'g')
			return (this.input_value.match(regex) || []).length > 0
		},
		is_column_selected() {
			const regex = RegExp(`${this.delimiter}`, 'g')
			return (this.input_value.match(regex) || []).length > 1
		},
		table_input() {
			return this.input_value.split(this.delimiter)[0]
		},
		column_input() {
			return this.input_value.split(this.delimiter)[1]
		},
		suggestions() {
			const [table, column] = this.input_value.split(this.delimiter)
			let suggestions = []

			if (!this.is_table_selected) {
				suggestions = table
					? this.table_list.filter((c) =>
							c.label.toLowerCase().includes(table.toLowerCase())
					  )
					: this.table_list
				suggestions = suggestions.map((s) => ({
					...s,
					is_table: true,
				}))
			} else if (!this.is_column_selected) {
				suggestions = column
					? this.column_list.filter((o) =>
							o.label.toLowerCase().includes(column.toLowerCase())
					  )
					: this.column_list
				suggestions = suggestions.map((s) => ({
					...s,
					is_column: true,
				}))
			}

			if (suggestions?.length > 50) {
				suggestions = suggestions.slice(0, 50)
			}

			return suggestions
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			if (suggestion.is_table) {
				this.query.get_selectable_columns.fetch({ tables: [suggestion] })
				this.input_value = `${suggestion.label}${this.delimiter}`
				this.table = suggestion
			} else if (suggestion.is_column) {
				this.input_value = `${this.table_input}${this.delimiter}${suggestion.label}${this.delimiter}`
				this.column = suggestion
			}
		},
		on_backspace(e) {
			// delete the previous selection if a delimiter is deleted
			const last_letter = e.target.value.slice(-1)
			if (last_letter && last_letter == this.delimiter) {
				e.stopPropagation()
				e.preventDefault()
				this.input_value = e.target.value
					.split(this.delimiter) // split by delimiter = [table, column]
					.filter((v) => v) // remove empty values = [table, column]
					.slice(0, -1) // remove last value = [table]
					.map((v) => `${v}${this.delimiter}`) // add delimiter = ['table;']
					.join('') // join by empty string = table;
			}
		},
		on_enter() {
			if (this.table && this.column) {
				this.$emit('column_selected', this.column)
				this.$refs.column_search?.blur()
				this.table = {}
				this.column = {}
				this.input_value = ''
				this.focused = false
			}
		},
	},
}
</script>
