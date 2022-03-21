<!-- This example requires Tailwind CSS v2.0+ -->
<template>
	<div class="">
		<div class="relative z-10 w-full rounded-md shadow-sm">
			<input
				type="text"
				name="table-search"
				class="block w-full rounded-md border-gray-300 text-sm focus:border-gray-300 focus:shadow focus:outline-0 focus:ring-0"
				placeholder="Select a table..."
				v-model="search_term"
				@focus="focused = true"
				@blur=";[focused, search_term] = [false, '']"
			/>
			<div
				class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
			>
				<FeatherIcon
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
					class="absolute top-10 mt-2 max-h-52 w-full origin-top overflow-scroll overflow-x-hidden rounded-md bg-white shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none"
				>
					<div
						v-for="item in suggestions"
						:key="item.label"
						class="flex cursor-default items-center justify-between rounded-md px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
						@click="select_table(item)"
					>
						<div class="flex items-center">
							<div class="font-semibold">{{ item.label }}</div>
						</div>
					</div>
				</div>
			</transition>
		</div>
	</div>
</template>

<script>
export default {
	data() {
		return {
			search_term: '',
			focused: false,
			suggestions: [],
		}
	},
	resources: {
		table_list() {
			return {
				method: 'analytics.api.get_table_list',
				params: {
					search_term: this.search_term,
				},
				auto: true,
				onSuccess() {
					this.suggestions = this.table_list
				},
				debounce: 300,
			}
		},
	},
	computed: {
		table_list() {
			return this.$resources.table_list.data || []
		},
	},
	methods: {
		select_table(table) {
			this.search_term = ''
			this.reset_suggestions()
			this.$emit('table_selected', table)
		},
		reset_suggestions() {
			this.suggestions = this.table_list
		},
	},
}
</script>
