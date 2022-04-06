<!-- This example requires Tailwind CSS v2.0+ -->
<template>
	<div class="">
		<div class="relative z-10 w-full rounded-md shadow-sm">
			<Input
				type="text"
				name="table-search"
				autocomplete="off"
				class="block h-9 w-full rounded-md border-gray-300 text-sm focus:border-gray-300 focus:bg-white focus:shadow focus:outline-0 focus:ring-0"
				placeholder="Select a table..."
				v-model="search_term"
				@input="(value) => (search_term = value)"
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
						@click="select_table(item)"
					>
						<div class="whitespace-pre font-semibold">{{ item.label }}</div>
						<div class="flex font-light text-gray-500">{{ item.source }}</div>
					</div>
				</div>
			</transition>
		</div>
	</div>
</template>

<script>
export default {
	props: ['query'],
	data() {
		return {
			search_term: '',
			focused: false,
		}
	},
	watch: {
		focused(is_focused) {
			is_focused && this.query.get_selectable_tables.fetch()
		},
	},
	computed: {
		table_list() {
			return this.query.get_selectable_tables?.data?.message || []
		},
		suggestions() {
			const suggestions = this.table_list.filter(
				(row) =>
					row.label.toLowerCase().indexOf(this.search_term.toLowerCase()) !== -1
			)
			// if (suggestions?.length > 20) {
			// 	return suggestions.slice(0, 30)
			// } else {
			return suggestions
			// }
		},
	},
	methods: {
		select_table(table) {
			this.search_term = ''
			this.$emit('table_selected', table)
		},
	},
}
</script>
