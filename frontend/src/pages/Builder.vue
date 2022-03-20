<template>
	<div class="flex flex-1 flex-col py-10">
		<header>
			<div
				class="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8"
			>
				<h1 class="text-3xl font-bold leading-tight text-gray-900">
					Query Builder
				</h1>
				<div class="">
					<button
						class="cursor-pointer rounded bg-white px-2.5 py-1 text-base shadow"
						@click="run_query"
						:disabled="$resources.query_result.loading"
					>
						Run Query
					</button>
				</div>
			</div>
		</header>
		<main class="flex flex-1">
			<div class="mx-auto flex max-w-7xl flex-1 sm:px-6 lg:px-8">
				<div class="my-8 grid flex-1 grid-flow-row auto-rows-fr gap-4">
					<div class="grid gap-4 sm:grid-cols-1 lg:grid-cols-3">
						<TablePicker @update:tables="(updated) => (tables = updated)" />
						<ColumnPicker
							:tables="table_names"
							@update:columns="(updated) => (columns = updated)"
						/>
						<FilterPicker
							:tables="table_names"
							@update:filters="(updated) => (filters = updated)"
						/>
					</div>
					<div class="flex">
						<QueryResult :data="query_result?.data" />
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
			columns: [],
			filters: {},
		}
	},
	computed: {
		table_names() {
			return this.tables.map((table) => table.label)
		},
		query_result() {
			return this.$resources.query_result.data
		},
	},
	resources: {
		query_result() {
			const { tables, columns, filters } = this
			return {
				method: 'analytics.api.fetch_query_result',
				params: { tables, columns, filters },
				onSuccess() {
					console.log(this.$resources.query_result.data)
				},
			}
		},
	},
	methods: {
		run_query() {
			if (this.tables?.length === 0 || this.columns?.length === 0) {
				this.$notify({
					icon: 'alert-circle',
					color: 'yellow',
					message: 'Please select at least one table and column',
					position: 'bottom',
				})
				return
			}
			this.$resources.query_result.fetch()
		},
	},
}
</script>
