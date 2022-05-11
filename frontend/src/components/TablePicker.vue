<template>
	<div class="flex min-h-[16rem] min-w-[22rem] flex-1 flex-col p-4">
		<TableSearch class="mb-4" :query="query" />
		<div
			v-if="tables.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No tables selected</p>
		</div>
		<div v-else class="flex flex-1 select-none flex-col divide-y divide-gray-200 overflow-scroll scrollbar-hide">
			<div
				v-for="(table, idx) in tables"
				:key="idx"
				class="flex cursor-pointer items-center justify-between space-x-8 p-2 text-sm text-gray-600 hover:bg-gray-50"
			>
				<div class="flex items-baseline">
					<div class="text-base font-medium">{{ table.label }}</div>
				</div>
				<div class="flex items-center px-1 py-0.5 text-gray-500 hover:text-gray-600" @click="remove_table(table)">
					<FeatherIcon name="x" class="h-3 w-3" />
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import TableSearch from './TableSearch.vue'

export default {
	name: 'TablePicker',
	props: ['query'],
	components: {
		TableSearch,
	},
	computed: {
		tables() {
			return this.query.doc.tables
		},
	},
	methods: {
		remove_table(table) {
			this.query.remove_table.submit({ table })
		},
	},
}
</script>
