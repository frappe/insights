<template>
	<div class="table-search relative z-10 w-full rounded-md shadow-sm">
		<Popover :show="input_focused">
			<template #target>
				<input
					type="text"
					ref="table_search"
					autocomplete="off"
					spellcheck="false"
					class="form-input block h-8 w-full select-none rounded-md text-sm placeholder-gray-500 focus:rounded-b-none focus:border focus:border-gray-200 focus:bg-white focus:shadow"
					:placeholder="input_focused ? 'Select a table...' : 'Add a table...'"
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
			if (e.target.closest('.table-search')) {
				return this.$refs.table_search.focus()
			}
			this.input_focused = false
		}
		document.addEventListener('click', this.outside_click_listener)

		this.query.get_selectable_tables.fetch(
			{},
			{
				onSuccess: () => {
					this.$refs.table_search.focus()
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
				this.query.get_selectable_tables.fetch()
			}
			if (!is_focused && is_focused != old_is_focused) {
				this.$emit('table_search_blur')
			}
		},
	},
	computed: {
		selectable_tables() {
			return this.query.get_selectable_tables?.data?.message || []
		},
		suggestions() {
			return this.input_value
				? this.selectable_tables.filter((t) => t.label.toLowerCase().includes(this.input_value.toLowerCase()))
				: this.selectable_tables
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			this.query.add_table.submit({ table: suggestion })
			this.reset()
		},
		reset() {
			this.$refs.table_search?.blur()
			this.input_value = ''
			this.input_focused = false
		},
	},
}
</script>
