<template>
	<div class="flex flex-col" v-if="query">
		<header class="mx-auto flex w-full max-w-7xl flex-col px-4 sm:px-6 lg:px-8">
			<div class="my-4 flex h-12 items-center justify-between">
				<div class="relative flex flex-col items-start">
					<input
						type="text"
						v-model="query.title"
						ref="title_input"
						spellcheck="false"
						@blur="on_title_update"
						:size="Math.max(query.title.length, 4)"
						@keydown.enter="on_title_update"
						class="peer border-none bg-transparent p-0 text-3xl font-bold caret-black focus:border-none focus:outline-none focus:ring-transparent"
					/>
					<div class="mt-2 flex space-x-2 text-sm font-light text-gray-500">
						<div class="flex items-center"><FeatherIcon name="database" class="mr-1 h-3 w-3" /> {{ data_source }}</div>
						<div class="flex items-center"><FeatherIcon name="layout" class="mr-1 h-3 w-3" /> {{ tables }}</div>
					</div>
				</div>
				<div class="flex items-center space-x-2">
					<QueryMenu :query="query" />
				</div>
			</div>
			<TabSwitcher :tabs="tabs" @tab_switched="(tab) => (active_tab = tab)" />
		</header>
		<!-- height = 100% - (padding-top (2) + padding-bottom (1.5) + header height (3))  -->
		<main class="flex h-[calc(100%-6.5rem)] flex-1">
			<div class="mx-auto flex max-w-7xl flex-1 flex-col sm:px-6 lg:px-8">
				<QueryBuilder v-show="active_tab == 'Build'" :query="$resources.query" />
				<QueryVisualizer v-if="active_tab == 'Visualize'" :query="$resources.query" />
			</div>
		</main>
	</div>
</template>

<script>
import TabSwitcher from '@/components/TabSwitcher.vue'
import QueryBuilder from '@/components/QueryBuilder.vue'
import QueryVisualizer from '@/components/QueryVisualizer.vue'
import QueryMenu from '@/components/QueryMenu.vue'

export default {
	name: 'Query',
	props: ['query_id'],
	components: {
		TabSwitcher,
		QueryBuilder,
		QueryVisualizer,
		QueryMenu,
	},
	data() {
		return {
			menu_open: false,
			active_tab: 'Build',
			tabs: ['Build', 'Visualize'],
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
					update_filters: 'update_filters',
					set_limit: 'set_limit',
					get_selectable_tables: 'get_selectable_tables',
					get_selectable_columns: 'get_selectable_columns',
					get_column_values: 'get_column_values',
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
		data_source() {
			return this.query.data_source
		},
		tables() {
			return this.query.tables.map((t) => t.label).join(', ')
		},
	},
	methods: {
		on_title_update() {
			if (!this.query.title || this.query.title.length == 0) {
				this.query.title = 'Untitled Query'
			}

			this.$resources.query.setValueDebounced.submit(
				{ title: this.query.title },
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
					},
				}
			)

			this.$refs.title_input.blur()
		},
	},
}
</script>
