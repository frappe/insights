<template>
	<div class="flex flex-1 flex-col py-10">
		<header>
			<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<h1 class="text-3xl font-bold leading-tight text-gray-900">
					Query Builder
				</h1>
			</div>
		</header>
		<main class="flex flex-1">
			<div class="mx-auto flex max-w-7xl flex-1 sm:px-6 lg:px-8">
				<div class="my-8 grid flex-1 grid-flow-row auto-rows-fr gap-4">
					<div class="grid gap-4 sm:grid-cols-1 lg:grid-cols-3">
						<TablePicker
							@update:table_list="(updated_list) => (tables = updated_list)"
						/>
						<ColumnPicker :tables="table_names" />
						<FilterPicker :tables="table_names" />
					</div>
					<div class="flex">
						<QueryResult />
					</div>
				</div>
			</div>
		</main>
	</div>
</template>

<script>
import TablePicker from '@/components/TablePicker.vue'
import ColumnPicker from '@/components/ColumnPicker.vue'
import FilterPicker from '@/components/FilterPicker.vue'
import QueryResult from '@/components/QueryResult.vue'

export default {
	name: 'Builder',
	components: {
		ColumnPicker,
		TablePicker,
		FilterPicker,
		QueryResult,
	},
	data() {
		return {
			tables: [],
		}
	},
	computed: {
		table_names() {
			return this.tables.map((table) => table.label)
		},
	},
}
</script>
