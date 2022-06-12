<template>
	<Popover class="flex w-full [&>div:first-child]:w-full">
		<template #target="{ isOpen, togglePopover }">
			<input
				type="text"
				ref="table_search"
				autocomplete="off"
				spellcheck="false"
				class="form-input block h-8 w-full select-none rounded-md text-sm placeholder-gray-500 focus:rounded-b-none focus:border focus:border-gray-200 focus:bg-white focus:shadow"
				:placeholder="isOpen ? 'Select a table...' : 'Add a table...'"
				v-model="input_value"
				@focus="togglePopover()"
			/>
		</template>
		<template #body="{ isOpen, togglePopover }">
			<SuggestionBox
				v-if="isOpen && filtered_options?.length"
				:header_and_suggestions="filtered_options"
				@option-select="
					(option) => {
						on_option_select(option)
						togglePopover()
					}
				"
			/>
		</template>
	</Popover>
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
		this.query.fetchTables.fetch(
			{},
			{
				onSuccess: () => {
					this.$refs.table_search.focus()
				},
			}
		)
	},
	computed: {
		table_options() {
			const tables = this.query.fetchTables?.data?.message || []
			return tables.filter((option, index, self) => {
				return self.findIndex((t) => t.table === option.table) === index
			})
		},
		filtered_options() {
			// filter out duplicates
			return this.input_value
				? this.table_options.filter((t) =>
						t.label.toLowerCase().includes(this.input_value.toLowerCase())
				  )
				: this.table_options
		},
	},
	methods: {
		on_option_select(option) {
			this.query.addTable.submit({ table: option })
			this.input_value = ''
			this.$emit('on-blur')
		},
	},
}
</script>
