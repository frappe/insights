<template>
	<div class="table-search relative z-10 w-full rounded-md shadow-sm">
		<Popover :show="show">
			<template #target>
				<input
					type="text"
					ref="table_search"
					autocomplete="off"
					spellcheck="false"
					class="form-input block h-8 w-full select-none rounded-md text-sm placeholder-gray-500 focus:rounded-b-none focus:border focus:border-gray-200 focus:bg-white focus:shadow"
					:placeholder="show ? 'Select a table...' : 'Add a table...'"
					v-model="input_value"
					@focus="show = true"
				/>
			</template>
			<template #content>
				<SuggestionBox
					v-if="show && suggestions?.length"
					:header_and_suggestions="suggestions"
					@option-select="on_suggestion_select"
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
			show: false,
		}
	},
	mounted() {
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest('.table-search')) {
				return this.$refs.table_search.focus()
			}
			this.show = false
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
		show(val, old_val) {
			if (val && val != old_val) {
				this.query.get_selectable_tables.fetch()
			}
			if (!val && val != old_val) {
				this.$emit('table_search_blur')
			}
		},
	},
	computed: {
		selectable_tables() {
			return this.query.get_selectable_tables?.data?.message || []
		},
		suggestions() {
			// filter out duplicates
			const _options = this.selectable_tables?.filter((option, index, self) => {
				return self.findIndex((t) => t.table === option.table) === index
			})
			return this.input_value
				? _options.filter((t) => t.label.toLowerCase().includes(this.input_value.toLowerCase()))
				: _options
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
			this.show = false
		},
	},
}
</script>
