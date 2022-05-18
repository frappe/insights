<template>
	<div v-if="query">
		<header class="flex flex-col border-b">
			<!-- Height 3 rem + Margin 2 rem -->
			<div class="flex h-[5rem] items-center justify-between py-4">
				<div class="relative flex flex-col items-start space-y-1">
					<input
						type="text"
						v-model="query.title"
						ref="title_input"
						spellcheck="false"
						@blur="on_title_update"
						:size="Math.max(query.title.length, 4)"
						@keydown.enter="on_title_update"
						class="peer -mx-2 -my-1 rounded border-none bg-transparent p-0 px-2 py-1 text-3xl font-bold caret-black focus:border-none focus:bg-gray-100/75 focus:outline-none focus:ring-transparent"
					/>
					<div class="flex space-x-2 text-sm font-light text-gray-600">
						<div v-if="data_source" class="flex items-center">
							<FeatherIcon name="database" class="mr-1 h-3 w-3" /> {{ data_source }}
						</div>
						<div v-if="tables" class="flex items-center">
							<FeatherIcon name="layout" class="mr-1 h-3 w-3" /> {{ tables }}
						</div>
					</div>
				</div>
				<div class="flex items-center space-x-2">
					<QueryMenu :query="query" />
				</div>
			</div>
			<!-- Height 2.5rem -->
			<TabSwitcher :tabs="tabs" @tab_switched="(tab) => (active_tab = tab)" />
		</header>
		<main class="flex h-[calc(100%-7.5rem)] w-full">
			<!-- height = 100% - Header Height  -->
			<QueryBuilder v-show="active_tab == 'Build'" :query="$resources.query" />
			<QueryTransform v-show="active_tab == 'Transform'" :query="$resources.query" />
			<QueryVisualizer v-if="active_tab == 'Visualize'" :query="$resources.query" />
		</main>
	</div>
</template>

<script>
import TabSwitcher from '@/components/TabSwitcher.vue'
import QueryBuilder from '@/components/QueryBuilder.vue'
import QueryTransform from '@/components/QueryTransform.vue'
import QueryVisualizer from '@/components/QueryVisualizer.vue'
import QueryMenu from '@/components/QueryMenu.vue'

export default {
	name: 'Query',
	props: ['query_id'],
	components: {
		TabSwitcher,
		QueryBuilder,
		QueryTransform,
		QueryVisualizer,
		QueryMenu,
	},
	data() {
		return {
			menu_open: false,
			active_tab: 'Build',
			tabs: ['Build', 'Transform', 'Visualize'],
		}
	},
	resources: {
		query() {
			return {
				type: 'document',
				doctype: 'Query',
				name: this.query_id,
				whitelistedMethods: {
					add_table: 'add_table',
					remove_table: 'remove_table',
					add_column: 'add_column',
					move_column: 'move_column',
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
