<template>
	<div class="flex flex-col pt-10 pb-5" v-if="query">
		<header>
			<div class="mx-auto flex h-12 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
				<div class="relative flex flex-col items-start">
					<input
						type="text"
						v-model="title"
						ref="title_input"
						spellcheck="false"
						@blur="on_title_update"
						:size="Math.max(title.length, 2)"
						@keydown.enter="on_title_update"
						class="peer border-none bg-transparent p-0 text-3xl font-bold caret-black focus:border-none focus:outline-none focus:ring-transparent"
					/>
					<div class="mt-1 text-sm text-gray-500">Data Source: {{ data_source }}</div>
				</div>
			</div>
		</header>
		<!-- height = 100% - (padding-top (2.5) + padding-bottom (1.5) + header height (3))  -->
		<main class="flex h-[calc(100%-7rem)] flex-1">
			<div class="mx-auto flex max-w-7xl flex-1 flex-col pt-8 sm:px-6 lg:px-8">
				<div class="h-full min-h-[12rem] flex-1 rounded-md bg-white shadow">
					<div class="flex h-16 flex-shrink-0">
						<QueryToolbar :query="$resources.query" />
					</div>
					<div class="flex h-[calc(100%-6.5rem)]">
						<QueryResult :result="result" :query="$resources.query" />
					</div>
					<div class="flex h-10 flex-shrink-0">
						<LimitsAndOrder :query="$resources.query" :limit="limit" />
					</div>
				</div>
			</div>
		</main>
	</div>
</template>

<script>
import QueryToolbar from '@/components/QueryToolbar.vue'
import QueryResult from '@/components/QueryResult.vue'
import LimitsAndOrder from '@/components/LimitsAndOrder.vue'

export default {
	name: 'QueryBuilder',
	props: ['query_id'],
	components: {
		QueryToolbar,
		QueryResult,
		LimitsAndOrder,
	},
	data() {
		return {
			title: 'Untitled Query',
			data_source: '',
			tables: [],
			columns: [],
			result: [],
			filters: {
				group_operator: 'All',
				level: 1,
				conditions: [],
			},
			limit: 100,
		}
	},
	resources: {
		query() {
			return {
				type: 'document',
				doctype: 'Query',
				name: this.query_id,
				whitelistedMethods: {
					add_column: 'add_column',
					update_column: 'update_column',
					remove_column: 'remove_column',
					update_columns: 'update_columns',
					update_filters: 'update_filters',
					get_selectable_tables: 'get_selectable_tables',
					get_selectable_columns: 'get_selectable_columns',
				},
				postprocess: (query) => {
					this.title = query.title
					this.data_source = query.data_source

					this.tables = query.tables.map((row) => {
						return {
							label: row.label,
							table: row.table,
						}
					})

					this.columns = query.columns

					// TODO: Fix if query.filters is undefined
					this.filters = JSON.parse(query.filters || '{}')

					this.result = JSON.parse(query.result || '[]')

					this.limit = query.limit
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
		on_column_update(updated_columns) {
			this.$resources.query.update_columns.submit({ updated_columns })
		},
		on_filter_update(updated_filters) {
			this.$resources.query.update_filters.submit({ updated_filters })
		},
	},
}
</script>
