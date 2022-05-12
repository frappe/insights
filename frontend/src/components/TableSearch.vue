<template>
	<div class="table-search relative z-10 w-full rounded-md shadow-sm">
		<Popover :show="input_focused">
			<template #target>
				<input
					type="text"
					ref="table_search"
					autocomplete="off"
					spellcheck="false"
					class="form-input block h-8 w-full select-none rounded-md border-gray-300 text-sm text-transparent placeholder-gray-500 caret-black focus:bg-gray-100"
					:placeholder="input_focused ? 'Select a table...' : 'Add a table...'"
					v-model="input_value"
					@focus="input_focused = true"
				/>
				<div
					v-if="input_value"
					class="absolute top-0 flex h-9 w-full cursor-text items-center whitespace-nowrap border border-transparent px-3 text-sm"
					@click="$refs.table_search.focus()"
				>
					{{ input_value.replace(/;/g, ' ') }}
				</div>
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
import SuggestionBox from './SuggestionBox.vue'

export default {
	props: ['query'],
	components: {
		SuggestionBox,
	},
	data() {
		return {
			table: {},
			input_value: '',
			input_focused: false,
		}
	},
	mounted() {
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest('.table-search')) {
				return this.$refs.table_search?.focus()
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
	},
	computed: {
		table_list() {
			return this.query.get_selectable_tables?.data?.message || []
		},
		suggestions() {
			return this.get_table_suggestions(this.input_value)
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			this.query.add_table.submit({ table: suggestion })
			this.reset()
		},
		reset() {
			this.$refs.table_search?.blur()
			this.table = {}
			this.input_value = ''
			this.input_focused = false
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
	},
}
</script>
