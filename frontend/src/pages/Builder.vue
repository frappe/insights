<template>
	<div class="flex flex-1 flex-col py-10" v-if="query">
		<header>
			<div
				class="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8"
			>
				<div class="relative flex items-center">
					<input
						type="text"
						v-model="title"
						ref="title_input"
						spellcheck="false"
						@blur="on_title_update"
						:size="Math.max(title.length, 2)"
						@keydown.enter="on_title_update"
						class="peer border-none bg-transparent p-0 text-3xl font-bold leading-tight text-transparent caret-black focus:border-none focus:outline-none focus:ring-transparent"
					/>
					<div
						class="absolute flex items-center whitespace-nowrap text-3xl font-bold leading-tight text-gray-900 hover:cursor-text"
						@click="$refs.title_input.focus()"
					>
						{{ title }}
						<FeatherIcon
							name="edit-2"
							class="ml-3 h-3.5 w-3.5 cursor-pointer text-gray-800 peer-focus:invisible"
							@click="$refs.title_input.focus()"
						/>
					</div>
				</div>
				<div class="">
					<Button appearance="white" @click="run_query"> Run Query </Button>
				</div>
			</div>
		</header>
		<main class="flex flex-1">
			<div class="mx-auto flex max-w-7xl flex-1 py-8 sm:px-6 lg:px-8">
				<div class="grid flex-1 grid-flow-row auto-rows-fr gap-4">
					<div class="grid gap-4 sm:grid-cols-1 lg:grid-cols-3">
						<TablePicker :tables="tables" @update:tables="on_table_update" />
						<ColumnPicker
							:tables="table_names"
							:columns="columns"
							@update:columns="on_column_update"
						/>
						<FilterPicker
							:filters="filters"
							:tables="table_names"
							@update:filters="on_filter_update"
						/>
					</div>
					<div class="flex">
						<QueryResult :data="result?.data" :columns="result?.columns" />
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
	props: ['query_id'],
	components: {
		ColumnPicker,
		TablePicker,
		FilterPicker,
		QueryResult,
	},
	data() {
		return {
			title: 'Untitled Query',
			tables: [],
			columns: [],
			filters: {
				group_operator: 'All',
				level: 1,
				conditions: [],
			},
		}
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
		query() {
			return {
				type: 'document',
				doctype: 'Query',
				name: this.query_id,
				whitelistedMethods: {
					update_tables: 'update_tables',
					update_columns: 'update_columns',
					update_filters: 'update_filters',
				},
				postprocess: (query) => {
					this.title = query.title
					this.tables = query.tables.map((row) => {
						return { label: row.table }
					})
					this.columns = query.columns.map(
						({ table, column_name, label, type, aggregation }) => {
							return { table, column_name, label, type, aggregation }
						}
					)
					// TODO: Fix if query.filters is undefined
					this.filters = JSON.parse(query.filters || '{}')
				},
				onError: () => {
					this.$notify({
						title: 'Something went wrong',
						color: 'red',
						icon: 'alert-circle',
					})
				},
			}
		},
	},
	computed: {
		table_names() {
			return this.tables.map((table) => table.label)
		},
		result() {
			return this.$resources.query_result.data
		},
		query() {
			return this.$resources.query.doc
		},
	},
	methods: {
		on_title_update() {
			if (!this.title || this.title.length == 0) {
				this.title = this.query.title || 'Untitled Query'
			} else if (this.title != this.query.title) {
				this.$resources.query.setValueDebounced.submit(
					{ title: this.title },
					{
						onSuccess: () => {
							this.$notify({
								title: 'Query title updated',
								color: 'green',
								icon: 'check',
							})
						},
						onError: () => {
							this.$notify({
								title: 'Something went wrong',
								color: 'red',
								icon: 'alert-circle',
							})
							this.title = this.query.title
						},
					}
				)
			}
			this.$refs.title_input.blur()
		},
		on_table_update(updated_tables) {
			this.$resources.query.update_tables.submit({ updated_tables })
		},
		on_column_update(updated_columns) {
			this.$resources.query.update_columns.submit({ updated_columns })
		},
		on_filter_update(updated_filters) {
			this.$resources.query.update_filters.submit({ updated_filters })
		},
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
