<template>
	<div class="flex flex-1 flex-col p-4">
		<ColumnPickerSearch
			class="mb-4"
			@column_selected="on_column_select"
			:tables="tables"
			:query="query"
		/>
		<div
			v-if="selected_columns.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No columns selected</p>
		</div>
		<div v-else class="flex flex-1 select-none flex-col">
			<div
				v-for="(column, list_idx) in selected_columns"
				:key="list_idx"
				class="menu-item flex h-10 cursor-pointer items-center justify-between border-b border-gray-200 pl-2 text-sm text-gray-700 hover:rounded-md hover:bg-gray-50"
				@click="menu_open_for = list_idx"
			>
				<div class="flex items-baseline">
					<span
						v-if="column.aggregation"
						class="my-0 flex-1 whitespace-nowrap font-medium text-blue-700"
					>
						{{ column.aggregation }}&nbsp;&#8226;&nbsp;
					</span>
					<div class="text-base font-semibold">
						{{ column.label }}
					</div>
				</div>
				<div class="flex items-center">
					<div class="mr-1 font-light text-gray-500">
						{{ column.table_label }}&nbsp;&#8226;&nbsp;{{ column.type }}
					</div>

					<div class="relative cursor-pointer rounded-md px-2 py-1">
						<MenuIcon />
						<!-- Hidden Menu -->
						<transition
							enter-active-class="transition ease-out duration-100"
							enter-from-class="transform opacity-0 scale-95"
							enter-to-class="transform opacity-100 scale-100"
							leave-active-class="transition ease-in duration-100"
							leave-from-class="transform opacity-100 scale-100"
							leave-to-class="transform opacity-0 scale-95"
						>
							<div
								v-if="menu_open_for == list_idx"
								class="absolute right-2 top-6 z-10 origin-top-right rounded-md bg-white shadow-md ring-1 ring-gray-200"
							>
								<div
									v-for="(item, menu_item_idx) in menu_items"
									:key="menu_item_idx"
									class="cursor-pointer px-3 py-1"
									:class="
										item.is_header
											? 'cursor-default border-b border-gray-200 text-xs font-light text-gray-500'
											: item.is_danger_action
											? 'border-t border-gray-200 text-red-400 hover:bg-gray-50'
											: item.is_aggregation
											? 'hover:bg-gray-50'
											: ''
									"
									@click="on_menu_item_select(item, list_idx)"
								>
									{{ item.label }}
								</div>
							</div>
						</transition>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import ColumnPickerSearch from './ColumnPickerSearch.vue'
import MenuIcon from './MenuIcon.vue'

export default {
	name: 'ColumnPicker',
	props: ['tables', 'columns', 'query'],
	components: {
		ColumnPickerSearch,
		MenuIcon,
	},
	data() {
		return {
			selected_columns: this.columns,
			menu_open_for: undefined,
		}
	},
	mounted() {
		// detect outside click to close agg menu
		document.addEventListener('click', (e) => {
			if (e.target.closest('.menu-item')) return
			this.menu_open_for = undefined
		})
	},
	resources: {
		aggregations() {
			return {
				method: 'analytics.api.get_aggregation_list',
				auto: true,
				debounce: 300,
			}
		},
	},
	computed: {
		aggregations() {
			return this.$resources.aggregations.data
		},
		menu_items() {
			const remove = { label: 'Remove', is_danger_action: true }
			const agg_header = { label: 'Aggregations', is_header: true }

			if (this.aggregations?.length) {
				const group_by = { label: 'Group By', is_aggregation: true }
				const aggregations = this.aggregations.map((label) => ({
					label,
					is_aggregation: true,
				}))
				return [agg_header, group_by, ...aggregations, remove]
			} else {
				return [remove]
			}
		},
	},
	methods: {
		on_column_select(column) {
			// check if column exists in selected_columns, if not then push
			const column_exists = this.selected_columns.find(
				(selected_column) =>
					selected_column.label === column.label &&
					selected_column.table === column.table
			)
			if (!column_exists) {
				this.selected_columns.push(column)
				this.$emit('update:columns', this.selected_columns)
			}
		},
		on_menu_item_select(agg, column_index) {
			if (agg.is_header) {
				return
			} else if (agg.is_aggregation) {
				this.selected_columns[column_index].aggregation = agg.label
			} else if (agg.is_danger_action) {
				this.selected_columns.splice(column_index, 1)
			}
			this.$emit('update:columns', this.selected_columns)
			this.menu_open_for = undefined
		},
	},
}
</script>
