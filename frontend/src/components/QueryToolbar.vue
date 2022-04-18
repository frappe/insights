<template>
	<div class="flex flex-1 items-center justify-between border-b border-gray-300 px-4 text-base text-gray-500">
		<div class="flex w-80 items-center">
			<ColumnSearch :query="query" />
		</div>
		<div class="flex items-center">
			<Popover :show="filter_popup_open">
				<template #target>
					<button
						class="add-filter-button ml-2 select-none rounded-md border border-gray-100 px-3 py-1 text-gray-600 shadow hover:bg-gray-50"
						:class="{
							'bg-blue-50 text-blue-400 ring-1 ring-blue-200 hover:bg-blue-50': filter_popup_open,
						}"
						@click="filter_popup_open = !filter_popup_open"
					>
						+ Add Filter
					</button>
				</template>
				<template #content>
					<div
						class="filter-picker-wrapper mt-2 flex min-h-[24rem] w-fit min-w-[32rem] origin-top-right rounded-md border bg-white shadow-md"
					>
						<FilterPicker :query="query" @update:filters="(filters) => query.update_filters.submit({ filters })" />
					</div>
				</template>
			</Popover>
		</div>
	</div>
</template>

<script>
import ColumnSearch from './ColumnSearch.vue'
import FilterPicker from './FilterPicker.vue'

export default {
	name: 'QueryToolbar',
	props: ['query'],
	components: {
		ColumnSearch,
		FilterPicker,
	},
	data() {
		return {
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
	},
}
</script>
