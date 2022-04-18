<template>
	<div class="column-search relative z-10 w-full rounded-md shadow-sm">
		<Popover :show="input_focused">
			<template #target>
				<input
					type="text"
					ref="column_search"
					autocomplete="off"
					spellcheck="false"
					class="form-input block h-8 w-full select-none rounded-md border-gray-300 text-sm font-medium text-transparent placeholder-gray-500 caret-black"
					:placeholder="input_focused ? 'Select a table...' : 'Add a column...'"
					v-model="input_value"
					@focus="input_focused = true"
				/>
				<div
					v-if="input_value"
					class="absolute top-0 flex h-9 w-full cursor-text items-center whitespace-nowrap border border-transparent px-3 text-sm"
					@click="$refs.column_search.focus()"
				>
					{{ input_value.replace(/;/g, ' ') }}
				</div>
			</template>
			<template #content>
				<SuggestionBox v-if="suggestions?.length" :suggestions="suggestions" @select="on_suggestion_select" />
			</template>
		</Popover>
	</div>
</template>

<script>
import SuggestionBox from './SuggestionBox.vue'

export default {
	props: ['query'],
	components: {
		SuggestionBox,
	},
	data() {
		return {
			input_value: '',
			input_focused: false,
			now_selecting: 'table',
			table: {},
			column: {},
		}
	},
	mounted() {
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest('.column-search') || e.target.classList.contains('column-picker-suggestion')) {
				return this.$refs.column_search?.focus()
			}
			this.input_focused = false
		}
		document.addEventListener('click', this.outside_click_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
	watch: {
		input_focused(is_focused, old_is_focused) {
			if (is_focused && is_focused != old_is_focused) {
				this.query.get_selectable_tables.fetch()
			}
		},
		input_value(new_value) {
			const delimiter_count = (new_value.match(/;/g) || []).length
			if (delimiter_count === 0) {
				this.table = {}
				this.column = {}
				this.now_selecting = 'table'
				return
			}
			if (delimiter_count === 1) {
				this.column = {}
				this.now_selecting = 'column'
				return
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
		suggestions() {
			const [table, column] = this.input_value.split(';')

			if (this.now_selecting === 'table') {
				return this.get_table_suggestions(table)
			}
			if (this.now_selecting === 'column') {
				return this.get_column_suggestions(column)
			}
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			if (this.now_selecting === 'table') {
				this.query.get_selectable_columns.fetch({ table: suggestion })
				this.input_value = `${suggestion.label};`
				this.table = suggestion
				this.now_selecting = 'column'
				this.$refs.column_search?.focus()
				return
			}

			if (this.now_selecting === 'column') {
				this.column = suggestion
				this.query.add_column.submit({ column: this.column })
				this.reset()
				return
			}
		},
		reset() {
			this.$refs.column_search?.blur()
			this.table = {}
			this.column = {}
			this.input_value = ''
			this.input_focused = false
			this.now_selecting = null
		},
		get_table_suggestions(input) {
			let _suggestions = []
			if (input) {
				_suggestions = this.table_list.filter((t) => t.label.toLowerCase().includes(input.toLowerCase()))
			} else {
				_suggestions = this.table_list
			}
			return _suggestions
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
			_suggestions = [{ label: 'Select a column...', is_header: true }, ..._suggestions]
			return _suggestions
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
	},
}
</script>
