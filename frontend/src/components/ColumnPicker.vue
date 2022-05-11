<template>
	<div class="flex min-h-[16rem] min-w-[26rem] flex-1 flex-col p-4">
		<ColumnSearch v-if="tables.length > 0" class="mb-4" :query="query" />
		<div
			v-if="tables.length > 0 && columns.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No columns selected</p>
		</div>
		<div v-else class="flex flex-1 select-none flex-col divide-y divide-gray-200 overflow-scroll scrollbar-hide">
			<div
				v-for="(column, idx) in columns"
				:key="idx"
				class="flex cursor-pointer items-center justify-between space-x-8 p-2 text-sm text-gray-600 hover:bg-gray-50"
			>
				<div class="flex items-baseline">
					<div class="text-base font-medium">{{ column.label }}</div>
				</div>
				<div class="flex items-center">
					<div class="font-light text-gray-500">{{ column.table_label }} &#8226; {{ column.type }}</div>
					<div
						class="ml-1 flex items-center px-1 py-0.5 text-gray-500 hover:text-gray-600"
						@click="remove_column(column)"
					>
						<FeatherIcon name="x" class="h-3 w-3" />
					</div>
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
	computed: {
		tables() {
			return this.query.doc.tables
		},
		columns() {
			return this.query.doc.columns
		},
	},
	methods: {
		remove_column(column) {
			this.query.remove_column.submit({ column })
		},
	},
}
</script>
