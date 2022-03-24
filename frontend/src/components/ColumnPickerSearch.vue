<!-- This example requires Tailwind CSS v2.0+ -->
<template>
	<div class="">
		<div class="relative z-10 w-full rounded-md shadow-sm">
			<Input
				type="text"
				name="column-search"
				class="block h-9 w-full rounded-md border-gray-300 text-sm focus:border-gray-300 focus:bg-white focus:shadow focus:outline-0 focus:ring-0"
				placeholder="Add a column..."
				v-model="search_term"
				@focus="focused = true"
				@blur=";[focused, search_term] = [false, '']"
			/>
			<div
				class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
			>
				<FeatherIcon
					v-if="focused"
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
						v-for="item in suggestions"
						:key="item.label"
						class="flex cursor-default items-center justify-between rounded-md px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
						@click="select_column(item)"
					>
						<div class="flex items-center">
							<div class="whitespace-pre font-semibold">{{ item.label }}</div>
						</div>
						<div class="flex font-light text-gray-500">
							{{ item.table }}&nbsp;&#8226;&nbsp;{{ item.type }}
						</div>
					</div>
				</div>
			</transition>
		</div>
	</div>
</template>

<script>
export default {
	props: ['tables'],
	data() {
		return {
			search_term: '',
			focused: false,
			suggestions: [],
		}
	},
	resources: {
		column_list() {
			return {
				method: 'analytics.api.get_column_list',
				params: {
					tables: this.tables,
				},
				auto: true,
				onSuccess() {
					this.suggestions = this.column_list
				},
			}
		},
	},
	computed: {
		column_list() {
			return this.$resources.column_list.data || []
		},
	},
	methods: {
		select_column(column) {
			this.search_term = ''
			this.reset_suggestions()
			this.$emit('column_selected', column)
		},
		reset_suggestions() {
			this.suggestions = this.column_list
		},
	},
	watch: {
		search_term(newValue) {
			if (!newValue) {
				this.reset_suggestions()
				return
			}
			this.suggestions = this.column_list.filter((column) => {
				return (
					column.label.toLowerCase().includes(newValue.toLowerCase()) ||
					column.table.toLowerCase().includes(newValue.toLowerCase())
				)
			})
		},
	},
}
</script>
