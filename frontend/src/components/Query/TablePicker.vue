<template>
	<div class="flex flex-1 flex-col px-4 pb-4">
		<div v-if="adding_table" class="mb-4 flex flex-shrink-0">
			<TableSearch :query="query" @table_search_blur="adding_table = false" />
		</div>
		<div v-else-if="!adding_table" class="mb-4 flex items-center justify-between">
			<div class="text-lg font-medium">Tables</div>
			<Button class="!flex !h-7 !w-7 !items-center !justify-center !p-0 !text-gray-700" @click="adding_table = true">
				+
			</Button>
		</div>
		<div
			v-if="tables.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No tables selected</p>
		</div>
		<div v-else class="-mt-2 flex flex-1 select-none flex-col divide-y overflow-y-scroll scrollbar-hide">
			<div
				v-for="(table, idx) in tables"
				:key="idx"
				class="flex h-10 cursor-pointer items-center justify-between space-x-8 pl-1 text-sm text-gray-600 hover:bg-gray-50"
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
import { ListItem } from 'frappe-ui'
import TableSearch from '@/components/Query/TableSearch.vue'

export default {
	name: 'TablePicker',
	props: ['query'],
	components: {
		ListItem,
		TableSearch,
	},
	data() {
		return {
			adding_table: false,
		}
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
