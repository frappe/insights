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
					update_filters: 'update_filters',
					set_limit: 'set_limit',
					get_selectable_tables: 'get_selectable_tables',
					get_selectable_columns: 'get_selectable_columns',
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
		title() {
			return this.query.title
		},
		data_source() {
			return this.query.data_source
		},
		tables() {
			return this.query.tables.map((row) => {
				return {
					label: row.label,
					table: row.table,
				}
			})
		},
		columns() {
			return this.query.columns
		},
		filters() {
			return JSON.parse(this.query.filters || '{}')
		},
		result() {
			return JSON.parse(this.query.result || '[]')
		},
		limit() {
			return this.query.limit
		},
	},
	methods: {
		on_title_update() {
			if (!this.title || this.title.length == 0) {
				this.title = this.query.title
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
	},
}
</script>
