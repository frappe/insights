<template>
	<div class="flex flex-1 items-center justify-between border-gray-300 text-base text-gray-600">
		<!-- Left Area -->
		<div class="flex items-center space-x-3">
			<Popover :show="table_popup_open">
				<template #target>
					<button
						class="add-table-button select-none rounded-md border border-gray-100 bg-gray-100 px-2.5 py-1 hover:bg-gray-200"
						@click="table_popup_open = !table_popup_open"
					>
						+ Add Table
					</button>
				</template>
				<template #content>
					<div class="table-picker-wrapper mt-2 flex origin-top-right rounded-md border bg-white shadow-md">
						<TablePicker :query="query" />
					</div>
				</template>
			</Popover>
			<Popover :show="column_popup_open" v-if="query.doc.tables?.length > 0">
				<template #target>
					<button
						class="add-column-button select-none rounded-md border border-gray-100 bg-gray-100 px-2.5 py-1 hover:bg-gray-200"
						@click="column_popup_open = !column_popup_open"
					>
						+ Add Column
					</button>
				</template>
				<template #content>
					<div class="column-picker-wrapper mt-2 flex origin-top-right rounded-md border bg-white shadow-md">
						<ColumnPicker :query="query" />
					</div>
				</template>
			</Popover>
			<Popover :show="filter_popup_open" v-if="query.doc.tables?.length > 0">
				<template #target>
					<button
						class="add-filter-button select-none rounded-md border border-gray-100 bg-gray-100 px-2.5 py-1 hover:bg-gray-200"
						@click="filter_popup_open = !filter_popup_open"
					>
						+ Add Filter
					</button>
				</template>
				<template #content>
					<div
						class="filter-picker-wrapper mt-2 flex min-h-[20rem] w-fit min-w-[26rem] origin-top-right rounded-md border bg-white shadow-md"
					>
						<FilterPicker :query="query" @update:filters="(filters) => query.update_filters.submit({ filters })" />
					</div>
				</template>
			</Popover>
		</div>
		<!-- Right Area -->
		<div class="flex items-center"></div>
	</div>
</template>

<script>
import TablePicker from './TablePicker.vue'
import ColumnPicker from './ColumnPicker.vue'
import FilterPicker from './FilterPicker.vue'

export default {
	name: 'QueryToolbar',
	props: ['query'],
	components: {
		TablePicker,
		ColumnPicker,
		FilterPicker,
	},
	data() {
		return {
			table_popup_open: false,
			column_popup_open: false,
			filter_popup_open: false,
		}
	},
	mounted() {
		// detect click outside of input
		document.addEventListener('click', (e) => {
			if (e.target.closest('.filter-picker-wrapper') || e.target.closest('.add-filter-button')) {
				return
			}
			this.filter_popup_open = false
		})

		document.addEventListener('click', (e) => {
			if (e.target.closest('.column-picker-wrapper') || e.target.closest('.add-column-button')) {
				return
			}
			this.column_popup_open = false
		})

		document.addEventListener('click', (e) => {
			if (e.target.closest('.table-picker-wrapper') || e.target.closest('.add-table-button')) {
				return
			}
			this.table_popup_open = false
		})
	},
}
</script>
