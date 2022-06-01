<template>
	<div class="column-search relative z-10 w-full rounded-md shadow-sm">
		<Popover :show="input_focused" :sameWidth="true">
			<template #target>
				<input
					type="text"
					ref="column_search"
					autocomplete="off"
					spellcheck="false"
					class="form-input block h-8 w-full select-none rounded-md text-sm placeholder-gray-500 focus:rounded-b-none focus:border focus:border-gray-200 focus:bg-white focus:shadow"
					:placeholder="input_focused ? 'Select a column...' : 'Add a column...'"
					v-model="input_value"
					@focus="input_focused = true"
				/>
			</template>
			<template #content>
				<SuggestionBox
					v-if="input_focused && suggestions?.length"
					:header_and_suggestions="suggestions"
					@select="on_suggestion_select"
				/>
			</template>
		</Popover>
	</div>
</template>

<script>
import SuggestionBox from '@/components/SuggestionBox.vue'

export default {
	props: ['query'],
	components: {
		SuggestionBox,
	},
	data() {
		return {
			input_value: '',
			input_focused: false,
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

		this.query.get_selectable_columns.fetch(
			{},
			{
				onSuccess: () => {
					this.$refs.column_search.focus()
				},
			}
		)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
	watch: {
		input_focused(is_focused, old_is_focused) {
			if (is_focused && is_focused != old_is_focused) {
				this.query.get_selectable_columns.fetch()
			}
			if (!is_focused && is_focused != old_is_focused) {
				this.$emit('column_search_blur')
			}
		},
	},
	computed: {
		column_list() {
			return this.query.get_selectable_columns?.data?.message || []
		},
		suggestions() {
			return this.get_column_suggestions(this.input_value)
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			this.query.add_column.submit({ column: suggestion })
			this.reset()
		},
		reset() {
			this.$refs.column_search?.blur()
			this.input_value = ''
			this.input_focused = false
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
