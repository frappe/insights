<template>
	<div class="flex min-h-[16rem] min-w-[22rem] flex-1 flex-col p-4">
		<ColumnSearch class="mb-4" :query="query" />
		<div
			v-if="columns.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No columns selected</p>
		</div>
		<div v-else class="flex flex-1 select-none flex-col divide-y divide-gray-200 overflow-scroll scrollbar-hide">
			<div
				v-for="(column, list_idx) in columns"
				:key="list_idx"
				class="flex cursor-pointer items-center justify-between space-x-8 p-2 text-sm text-gray-600 hover:bg-gray-50"
				@click="menu_open_for = list_idx"
			>
				<div class="flex items-baseline">
					<div class="text-base font-medium">{{ column.label }}</div>
				</div>
				<div class="flex items-center">
					<div class="font-light text-gray-500">{{ column.table_label }} &#8226; {{ column.type }}</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import ColumnSearch from './ColumnSearch.vue'

export default {
	name: 'ColumnPicker',
	props: ['query'],
	components: {
		ColumnSearch,
	},
	mounted() {
		// detect outside click to close agg menu
		document.addEventListener('click', (e) => {
			if (e.target.closest('.menu-item')) return
			this.menu_open_for = undefined
		})
	},
	computed: {
		columns() {
			return this.query.doc.columns
		},
	},
}
</script>
