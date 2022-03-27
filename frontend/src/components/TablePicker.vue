<template>
	<div class="flex flex-col rounded-md bg-white p-4 shadow">
		<TablePickerSearch class="mb-4" @table_selected="on_table_select" />
		<div
			v-if="selected_tables.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>Add tables to build report upon...</p>
		</div>
		<div v-else class="flex flex-1 select-none flex-col">
			<div
				v-for="(table, list_idx) in selected_tables"
				:key="list_idx"
				class="menu-item flex h-10 cursor-default items-center justify-between border-b border-gray-300 pl-2 text-sm text-gray-700 hover:rounded-md hover:bg-gray-50"
				@click="menu_open_for = list_idx"
			>
				<div class="text-base font-medium">{{ table.label }}</div>
				<div class="flex items-center">
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
											? 'cursor-default border-b border-gray-200 text-xs font-light text-gray-400'
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
import TablePickerSearch from './TablePickerSearch.vue'
import MenuIcon from './MenuIcon.vue'

export default {
	name: 'TablePicker',
	props: ['tables'],
	components: {
		TablePickerSearch,
		MenuIcon,
	},
	data() {
		return {
			selected_tables: this.tables,
			menu_open_for: undefined,
			menu_items: [{ label: 'Remove', is_danger_action: true }],
		}
	},
	mounted() {
		// detect outside click to close menu
		document.addEventListener('click', (e) => {
			if (e.target.closest('.menu-item')) return
			this.menu_open_for = undefined
		})
	},
	methods: {
		on_table_select(table) {
			// check if table exists in selected_tables, if not then push
			const table_exists = this.selected_tables.find(
				(selected_table) => selected_table.label === table.label
			)
			if (!table_exists) {
				this.selected_tables.push(table)
				this.$emit('update:tables', this.selected_tables)
			}
		},
		on_menu_item_select(item, table_index) {
			if (item.is_danger_action) {
				this.selected_tables.splice(table_index, 1)
			}
			this.$emit('update:tables', this.selected_tables)
			this.menu_open_for = undefined
		},
	},
}
</script>
